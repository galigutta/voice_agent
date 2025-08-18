#!/bin/bash

# Test script to check terminal detection

echo "Testing terminal detection..."
echo "Please ensure this script is run from a terminal window"
echo ""

# Get the active window class
WINDOW_CLASS=$(xprop -id $(xdotool getactivewindow) WM_CLASS 2>/dev/null | grep -o '"[^"]*"')

echo "Raw window class values detected:"
echo "$WINDOW_CLASS"
echo ""

# Convert to lowercase for comparison
WINDOW_CLASS_LOWER=$(echo "$WINDOW_CLASS" | tr '[:upper:]' '[:lower:]')

echo "Lowercase window class values:"
echo "$WINDOW_CLASS_LOWER"
echo ""

# Check if it's a terminal
if echo "$WINDOW_CLASS_LOWER" | grep -qiE '(terminal|konsole|xterm|rxvt|kitty|alacritty|gnome-terminal|terminator|tilix|urxvt|st-256color|wezterm|foot)'; then
    echo "✓ Terminal detected! Will use Ctrl+Shift+v for pasting"
else
    echo "✗ Not detected as terminal. Will use Ctrl+v for pasting"
    echo ""
    echo "If this is incorrect, please report the window class values above"
    echo "so we can add your terminal to the detection list."
fi

echo ""
echo "Testing clipboard paste in 3 seconds..."
echo "Sample text" | xclip -selection c
sleep 3

if echo "$WINDOW_CLASS_LOWER" | grep -qiE '(terminal|konsole|xterm|rxvt|kitty|alacritty|gnome-terminal|terminator|tilix|urxvt|st-256color|wezterm|foot)'; then
    xdotool key Ctrl+Shift+v
else
    xdotool key Ctrl+v
fi