#!/usr/bin/env bats

setup() {
  export PATH="${BATS_TEST_DIRNAME}/../bin:$PATH"
  export MOCK_BACKLIGHT_DIR="${BATS_TEST_TMPDIR}/backlight"
  mkdir -p "$MOCK_BACKLIGHT_DIR"

  # Set the BACKLIGHT_PATH variable so g15-daemon.sh uses our mock
  BACKLIGHT_PATH="$MOCK_BACKLIGHT_DIR"
}

@test "get_screen_brightness_perc returns correct value when directory exists" {
  echo "50" > "$MOCK_BACKLIGHT_DIR/brightness"
  echo "100" > "$MOCK_BACKLIGHT_DIR/max_brightness"

  source "${BATS_TEST_DIRNAME}/../bin/g15-daemon.sh"

  run get_screen_brightness_perc
  [ "$status" -eq 0 ]
  [ "$output" -eq 50 ]
}

@test "get_screen_brightness_perc calculates correctly with different max" {
  echo "255" > "$MOCK_BACKLIGHT_DIR/brightness"
  echo "255" > "$MOCK_BACKLIGHT_DIR/max_brightness"

  source "${BATS_TEST_DIRNAME}/../bin/g15-daemon.sh"

  run get_screen_brightness_perc
  [ "$status" -eq 0 ]
  [ "$output" -eq 100 ]
}

@test "get_screen_brightness_perc returns 100 when directory does not exist" {
  export BACKLIGHT_PATH="${BATS_TEST_TMPDIR}/non_existent_backlight"

  source "${BATS_TEST_DIRNAME}/../bin/g15-daemon.sh"

  run get_screen_brightness_perc
  [ "$status" -eq 0 ]
  [ "$output" -eq 100 ]
}
