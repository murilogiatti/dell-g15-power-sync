#!/usr/bin/env bats

setup() {
  export PATH="${BATS_TEST_DIRNAME}/../bin:$PATH"
  export MOCK_SYSFS_DIR="${BATS_TEST_TMPDIR}/sysfs_backlight"
  export MOCK_BACKLIGHT_DIR="${MOCK_SYSFS_DIR}/amdgpu_bl2"
  export MOCK_LOG="${BATS_TEST_TMPDIR}/openrgb.log"
  mkdir -p "$MOCK_BACKLIGHT_DIR"

  # Source the daemon script in test mode
  # shellcheck disable=SC1091
  source "${BATS_TEST_DIRNAME}/../bin/g15-daemon.sh"

  BACKLIGHT_SYSFS_DIR="$MOCK_SYSFS_DIR"
  BACKLIGHT_PATH="$MOCK_BACKLIGHT_DIR"
  LAST_STATE=""

  openrgb() {
    echo "$*" >> "$MOCK_LOG"
    return 0
  }
  export -f openrgb
}

@test "update_screen_brightness_perc calculates percentage accurately" {
  echo "50" > "$MOCK_BACKLIGHT_DIR/brightness"
  echo "100" > "$MOCK_BACKLIGHT_DIR/max_brightness"

  update_screen_brightness_perc
  [ "$BRIGHTNESS_PERC" -eq 50 ]
}

@test "update_screen_brightness_perc scales non-100 max_brightness" {
  echo "128" > "$MOCK_BACKLIGHT_DIR/brightness"
  echo "255" > "$MOCK_BACKLIGHT_DIR/max_brightness"

  update_screen_brightness_perc
  [ "$BRIGHTNESS_PERC" -eq 50 ]
}

@test "update_screen_brightness_perc falls back to 100 when directory does not exist" {
  rm -rf "$MOCK_SYSFS_DIR"
  BACKLIGHT_PATH="${MOCK_SYSFS_DIR}/non_existent"

  update_screen_brightness_perc
  [ "$BRIGHTNESS_PERC" -eq 100 ]
}

@test "update_screen_brightness_perc falls back to alternate amdgpu_bl0 directory" {
  rm -rf "$MOCK_BACKLIGHT_DIR"
  mkdir -p "${MOCK_SYSFS_DIR}/amdgpu_bl0"
  echo "30" > "${MOCK_SYSFS_DIR}/amdgpu_bl0/brightness"
  echo "100" > "${MOCK_SYSFS_DIR}/amdgpu_bl0/max_brightness"

  update_screen_brightness_perc
  [ "$BRIGHTNESS_PERC" -eq 30 ]
}

@test "apply_settings maps all 5 brightness zones to safe white hex values" {
  echo "100" > "$MOCK_BACKLIGHT_DIR/max_brightness"

  # Zone 10% (0-20%) -> 23 -> 171717
  echo "15" > "$MOCK_BACKLIGHT_DIR/brightness"
  apply_settings
  [ "$LAST_STATE" = "10" ]
  grep -q "\-c 171717" "$MOCK_LOG"

  # Zone 30% (21-40%) -> 69 -> 454545
  echo "35" > "$MOCK_BACKLIGHT_DIR/brightness"
  apply_settings
  [ "$LAST_STATE" = "30" ]
  grep -q "\-c 454545" "$MOCK_LOG"

  # Zone 50% (41-60%) -> 115 -> 737373
  echo "55" > "$MOCK_BACKLIGHT_DIR/brightness"
  apply_settings
  [ "$LAST_STATE" = "50" ]
  grep -q "\-c 737373" "$MOCK_LOG"

  # Zone 75% (61-80%) -> 172 -> ACACAC
  echo "75" > "$MOCK_BACKLIGHT_DIR/brightness"
  apply_settings
  [ "$LAST_STATE" = "75" ]
  grep -q "\-c ACACAC" "$MOCK_LOG"

  # Zone 100% (81-100%) -> 230 -> E6E6E6
  echo "95" > "$MOCK_BACKLIGHT_DIR/brightness"
  apply_settings
  [ "$LAST_STATE" = "100" ]
  grep -q "\-c E6E6E6" "$MOCK_LOG"
}

@test "apply_settings does not update LAST_STATE when openrgb fails" {
  echo "100" > "$MOCK_BACKLIGHT_DIR/max_brightness"
  echo "50" > "$MOCK_BACKLIGHT_DIR/brightness"

  openrgb() {
    return 1
  }

  apply_settings
  [ -z "$LAST_STATE" ]
}
