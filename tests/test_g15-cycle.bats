#!/usr/bin/env bats

setup() {
  export PATH="${BATS_TEST_DIRNAME}/../bin:$PATH"

  # We mock `powerprofilesctl` to simulate the behavior.
  export MOCK_POWER_PROFILE="power-saver"

  powerprofilesctl() {
    if [[ "$1" == "get" ]]; then
      echo "$MOCK_POWER_PROFILE"
    elif [[ "$1" == "set" ]]; then
      MOCK_POWER_PROFILE="$2"
    fi
  }
  export -f powerprofilesctl
}

@test "g15-cycle.sh transitions from power-saver to balanced" {
  export MOCK_POWER_PROFILE="power-saver"
  
  # Run the script, but we need to source it so it modifies the MOCK_POWER_PROFILE in the current shell
  # Wait, standard bash subshells won't modify parent MOCK_POWER_PROFILE. 
  # Let's modify g15-cycle.sh to use `powerprofilesctl set` and verify the call.

  # Mock `powerprofilesctl` and capture calls
  function powerprofilesctl() {
    echo "$1 $2" >> "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
    if [[ "$1" == "get" ]]; then
      echo "$MOCK_POWER_PROFILE"
    fi
  }
  export -f powerprofilesctl

  export MOCK_POWER_PROFILE="power-saver"
  run bash "${BATS_TEST_DIRNAME}/../bin/g15-cycle.sh"
  [ "$status" -eq 0 ]
  run grep "set balanced" "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
  [ "$status" -eq 0 ]
}

@test "g15-cycle.sh transitions from balanced to performance" {
  export MOCK_POWER_PROFILE="balanced"

  function powerprofilesctl() {
    echo "$1 $2" >> "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
    if [[ "$1" == "get" ]]; then
      echo "$MOCK_POWER_PROFILE"
    fi
  }
  export -f powerprofilesctl

  run bash "${BATS_TEST_DIRNAME}/../bin/g15-cycle.sh"
  [ "$status" -eq 0 ]
  run grep "set performance" "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
  [ "$status" -eq 0 ]
}

@test "g15-cycle.sh transitions from performance to power-saver" {
  export MOCK_POWER_PROFILE="performance"

  function powerprofilesctl() {
    echo "$1 $2" >> "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
    if [[ "$1" == "get" ]]; then
      echo "$MOCK_POWER_PROFILE"
    fi
  }
  export -f powerprofilesctl

  run bash "${BATS_TEST_DIRNAME}/../bin/g15-cycle.sh"
  [ "$status" -eq 0 ]
  run grep "set power-saver" "${BATS_TEST_TMPDIR}/powerprofilesctl.log"
  [ "$status" -eq 0 ]
}
