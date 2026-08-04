#!/usr/bin/env bash

set -euo pipefail

token_file="${KAGGLE_TOKEN_FILE:-$HOME/.kaggle/access_token}"

if [[ ! -r "$token_file" ]]; then
  printf 'Kaggle token is not readable: %s\n' "$token_file" >&2
  exit 1
fi

token="$(tr -d '\r\n' < "$token_file")"

if [[ ! "$token" =~ ^[A-Za-z0-9_-]{20,}$ ]]; then
  printf 'Kaggle token is empty or malformed: %s\n' "$token_file" >&2
  exit 1
fi

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s https://api.kaggle.com/...\n' "$0" >&2
  exit 1
fi

url="$1"
case "$url" in
  https://api.kaggle.com/*) ;;
  *)
    printf 'Refusing to send credentials outside https://api.kaggle.com/\n' >&2
    exit 1
    ;;
esac

# Supplying the header through curl's standard-input config keeps the token out
# of the process command line and prevents arbitrary curl options from callers.
printf 'header = "Authorization: Bearer %s"\n' "$token" |
  curl --config - --fail --silent --show-error --request GET "$url"
