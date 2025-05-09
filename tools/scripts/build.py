#!/usr/bin/env python

import os
import platform
import shutil
import subprocess
import sys

# Change to project directory if we are not already there
current_directory = os.getcwd()
if not os.path.exists(os.path.join(f"{current_directory}", "game")):
    os.chdir("..")
    os.chdir("..")

project_directory = os.getcwd()

platform_arg = sys.argv[1]
configuration = sys.argv[2]
architecture = sys.argv[3]
precision = sys.argv[4]
is_ci = False
if len(sys.argv) == 6:
    is_ci = sys.argv[5]

# ===============================================
# Visual Studio 2022 specific stuff
if platform_arg == "Win32" or platform_arg == "x64":
    platform_arg = "windows"

# Visual Studio 2022 doesn't seem to have a separate setting for architecture, so it's bundled in with the platform.
# Have to parse it out separately in these scripts to get the correct one.
# E.g. windows_x86_64 -> x86_64
if architecture == "Win32":
    architecture = "x86_32"
elif architecture == "x64" or architecture == "linux":
    architecture = "x86_64"
elif architecture == "web":
    architecture = "wasm32"
elif architecture == "android": # TODO: Add different android processor platforms? E.g. android_arm32, android_arm64, android_x86_32, android_x86_64?
    architecture = "arm64"
    
using_wsl = (platform.system() == "Windows") and (platform_arg == "linux")

# ===============================================
# Build Godot
os.chdir("godot")

if configuration in ["editor", "editor_game"] or is_ci:
    print("Build Godot Engine", flush=True)
    
    build_command = ""
    if using_wsl:
        build_command = "wsl "
    
    if configuration == "production":
        build_command += f"scons platform={platform_arg} target=editor arch={architecture} precision={precision} production=yes"
    elif configuration == "profile":
        build_command += f"scons platform={platform_arg} target=editor arch={architecture} precision={precision} production=yes debug_symbols=yes"
        if is_ci:   # engine debug symbols are too large for CI
            build_command = build_command.replace(" debug_symbols=yes", "")
    elif configuration == "template_release":
        build_command += f"scons platform={platform_arg} target=editor arch={architecture} precision={precision}"
    else:
        build_command += f"scons platform={platform_arg} target=editor arch={architecture} precision={precision} dev_build=yes dev_mode=yes"
        if is_ci:   # Same as above...
            build_command = build_command.replace(" dev_build=yes dev_mode=yes", "")

    if is_ci:
        build_command += " debug_symbols=no tests=yes"

    # Removing dev_build/dev_mode from web editor because it doesn't compile (get emscripten errors...) and adding dlink_enabled
    if platform_arg == "web":
        if configuration in ["editor", "editor_game", "template_debug"]:
            build_command = build_command.replace(" dev_build=yes dev_mode=yes", "")
        
        build_command += " dlink_enabled=yes threads=no"
        
    elif platform_arg == "android":
        build_command += " generate_apk=yes"
        
    print("Build Command: " + build_command)
    return_code = subprocess.call(build_command, shell=True)
    if return_code != 0:
        sys.exit(f"Error: Failed to build godot for {platform_arg} {configuration} {architecture} {precision}")
    
    if platform_arg == "web" and configuration in ["editor", "editor_game"]:
        print(os.getcwd(), flush=True)
        os.chdir(os.path.join("bin", ".web_zip"))
        
        godot_html_editor_file_name = "godot.editor.html"
        if os.path.isfile(godot_html_editor_file_name):
            shutil.copyfile(godot_html_editor_file_name, "index.html")
            
        os.chdir(os.path.join("..", ".."))

# ===============================================
# Generate C++ extension api files
print("Generate C++ extension api files", flush=True)
os.chdir("bin")

# TEMP DEBUGGING CI
print(f"Current Working Directory: {os.getcwd()} has files: ", flush=True)
for (search_path,directory_names,files) in os.walk(os.getcwd(), topdown=True):
    search_path_with_ending_slash = os.path.join(search_path, '').replace('\\', '/')
    
    for (file) in files:
        print(str(search_path_with_ending_slash + file), flush=True)

godot_engine_architecture = ""
is_os_64_bit = sys.maxsize > 2**32
if is_os_64_bit:
    godot_engine_architecture = "x86_64"
else:
    godot_engine_architecture = "x86_32"

godot_binary_file_name = ""
if platform.system() == "Windows":
    godot_binary_file_name = f"godot.windows.editor.dev.{godot_engine_architecture}.exe"
elif platform.system() == "Linux":
    godot_binary_file_name = f"godot.linuxbsd.editor.dev.{godot_engine_architecture}"
elif platform.system() == "Darwin":
    godot_binary_file_name = f"godot.macos.editor.dev.{godot_engine_architecture}"

if configuration in ["template_release", "profile", "production"] or is_ci:
    godot_binary_file_name = godot_binary_file_name.replace(".dev", "")

if precision == "double":
    godot_binary_file_name = godot_binary_file_name.replace(f"{godot_engine_architecture}", f"{precision}.{godot_engine_architecture}")

build_command = ""
if using_wsl:
    build_command = "wsl ./"
if platform.system() == "Linux":
    print(f"Called chmod +x {godot_binary_file_name}", flush=True)
    subprocess.call(f"chmod +x {godot_binary_file_name}", shell=True)
    build_command += "./"
build_command += f"{godot_binary_file_name} --headless --dump-extension-api --dump-gdextension-interface"

return_code = subprocess.call(build_command, shell=True)
if return_code != 0:
    sys.exit(f"Error: Failed to generate C++ extension api files from {godot_binary_file_name}")

try:
    shutil.copy(os.path.join(f"{os.getcwd()}", "extension_api.json"), os.path.join(f"{project_directory}", "godot-cpp", "gdextension", "extension_api.json"))
    shutil.copy(os.path.join(f"{os.getcwd()}", "gdextension_interface.h"), os.path.join(f"{project_directory}", "godot-cpp", "gdextension", "gdextension_interface.h"))
except IOError as e:
    sys.exit(f"Error: Failed to copy extension api files from godot/bin -> godot_cpp/gdextension/ {e}")

# ===============================================
# Build Game
print("Build Game", flush=True)
os.chdir("..")
os.chdir("..")

build_command = ""
if using_wsl:
    build_command = "wsl "
    
if configuration == "production":
    build_command += f"scons platform={platform_arg} target={configuration} arch={architecture} precision={precision} production=yes"
elif configuration == "profile":
    build_command += f"scons platform={platform_arg} target={configuration} arch={architecture} precision={precision} production=yes debug_symbols=yes"
elif configuration == "template_release":
    build_command += f"scons platform={platform_arg} target={configuration} arch={architecture} precision={precision}"
else:
    build_command += f"scons platform={platform_arg} target={configuration} arch={architecture} precision={precision} dev_build=yes dev_mode=yes"

if platform_arg == "web":
    if configuration in ["editor", "editor_game", "template_debug"]:
        build_command = build_command.replace(" dev_build=yes dev_mode=yes", "")
    build_command += " threads=no"
    
return_code = subprocess.call(build_command, shell=True)
if return_code != 0:
    sys.exit(f"Error: Failed to build game for {platform_arg} {configuration} {architecture} {precision}")

# ===============================================
# (Web Only) Zip Project
if platform_arg == "web" and configuration == "editor":
    print("Zip Game Project For Web Editor", flush=True)
    
    # Remove the old folder
    if os.path.isdir("game.zip"):
        shutil.rmtree("game.zip", True)

    # Make new zip folder
    shutil.make_archive("game", "zip", "game")
    