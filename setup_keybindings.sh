#!/usr/bin/env bash

# Machine-specific keybinding setup for voice agent
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTNAME_LOWER=$(hostname | tr '[:upper:]' '[:lower:]')

echo "Setting up voice agent keybindings for: $HOSTNAME_LOWER"

# Determine keys based on machine type
if [[ "$HOSTNAME_LOWER" == *"thinkpad"* ]]; then
    PRIMARY_KEY="XF86Favorites"
    MACHINE_TYPE="ThinkPad (laptop)"
elif [[ "$HOSTNAME_LOWER" == *"desktop"* ]]; then
    PRIMARY_KEY="Menu"
    MACHINE_TYPE="Desktop"
else
    # Default fallback
    PRIMARY_KEY="F12"
    MACHINE_TYPE="Unknown (using F12)"
fi

echo "Machine type: $MACHINE_TYPE"
echo "Primary key: $PRIMARY_KEY"
echo ""

# Set up the keybindings
echo "Configuring keybindings..."

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ name 'Voice Dictation'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ command "$SCRIPT_DIR/toggle_dictation.sh"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ binding "$PRIMARY_KEY"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ name 'Voice Dictation Append Mode'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ command "$SCRIPT_DIR/toggle_dictation_append.sh"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/ binding "<Control>$PRIMARY_KEY"

# Register the keybindings
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/', '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom1/']"

echo "✅ Keybindings configured for $MACHINE_TYPE"
echo ""
echo "Voice agent controls:"
echo "  $PRIMARY_KEY → Regular dictation"
echo "  Ctrl+$PRIMARY_KEY → Append mode dictation"