#!/bin/zsh
# setup-workstation.sh -- rebuild the Node60 design environment on an Apple-silicon Mac, then
# check that the machine reproduces the process. Safe to re-run: it installs only what is missing
# or wrong, prints every change, and never touches an existing git checkout.
#
#   scripts/setup-workstation.sh              install what's missing, then verify (incl. one judging run)
#   scripts/setup-workstation.sh --check      change nothing; report, then verify
#   options:  --no-judge        skip the timed judging run (7-36 min) in the verification
#             --extras          also install the reference Mac's other Homebrew packages (not needed)
#             --no-plugins      don't install the Claude Code plugins (dropout-hardware, kicad-happy)
#             --update-krt      fast-forward an existing ~/Dev/KiCadRoutingTools to origin/main (off by
#                               default: other sessions' runs may be using that checkout)
#             --krt-at WHICH    KRT for the judging run: 'reference' (default; a temp copy of the reference
#                               run's commit, so the result must match) or 'live' (the checkout as it is)
#             --ref REF         node60-hw commit to verify (default: the reference run's commit, REF_JUDGE_COMMIT)
#             --judge-out DIR   where the judging run goes (default ~/Dev/node60-judge-runs/<host>-<time>)
#
# Pins and reference versions: scripts/workstation/pins.env. How-to: scripts/workstation/README.md.
# The layout is recreated as on the reference Mac (~/Dev/..., ~/.cache/dropout/krt-venv,
# /Applications/KiCad), because the judging scripts hard-code it. It follows the handbook's
# "Setting up a new Mac" (chapter 07) and adds what Node60's placement process needs.
emulate zsh
setopt pipe_fail no_unset
HERE=${0:A:h}
source $HERE/workstation/pins.env

CHECK=0 JUDGE=1 EXTRAS=0 PLUGINS_ON=1 UPDATE_KRT=0 KRT_AT=reference REF="" JOUT=""
while (( $# )); do
  case $1 in
    --check) CHECK=1 ;;
    --no-judge) JUDGE=0 ;;
    --extras) EXTRAS=1 ;;
    --no-plugins) PLUGINS_ON=0 ;;
    --update-krt) UPDATE_KRT=1 ;;
    --krt-at) KRT_AT=$2; shift ;;
    --ref) REF=$2; shift ;;
    --judge-out) JOUT=$2; shift ;;
    -h|--help) sed -n '2,22p' $0; exit 0 ;;
    *) print -u2 "unknown option $1"; exit 2 ;;
  esac
  shift
done

DEV=$HOME/Dev
KRT=$HOME/$KRT_DIR_REL
VENV=$HOME/$KRT_VENV_REL
CHANGES=() WARNS=() FAILS=()
say()    { printf '  %-26s %s\n' "$1" "$2"; }
ok()     { say "$1" "ok  $2"; }
changed(){ say "$1" "CHANGED  $2"; CHANGES+=("$1: $2"); }
warn()   { say "$1" "WARN  $2"; WARNS+=("$1: $2"); }
fail()   { say "$1" "FAIL  $2"; FAILS+=("$1: $2"); }
would()  { say "$1" "MISSING  (would run: $2)"; WARNS+=("$1: missing, --check"); }
section(){ print; print -- "== $1"; }
# do_or_would NAME "command ..." : run it (install mode) or say what would run (--check)
do_or_would() {
  local name=$1; shift
  if (( CHECK )); then would $name "$*"; return 1; fi
  print -- "    \$ $*"; "$@"
}

# ---------------------------------------------------------------------------------------------
section "Hardware and macOS"
if [[ $(uname -m) != arm64 ]]; then
  fail "CPU" "$(uname -m): Apple silicon (arm64) only; KRT's router binary pin is the arm64 build"; exit 1
fi
P=$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo 0)
E=$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo 0)
MEM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
say "Model" "$(sysctl -n hw.model), $(sysctl -n machdep.cpu.brand_string)"
say "Cores" "$P performance + $E efficiency"
say "Memory" "$MEM_GB GB"
# One judging run peaks at about 1.6 GB (reference timing.tsv); the router is single-threaded.
PEAK_MB=$(awk -F'\t' 'NR>1 && $5>m {m=$5} END {print m+0}' $HERE/workstation/reference/timing.tsv 2>/dev/null || echo 0)
(( PEAK_MB > 0 )) || PEAK_MB=2048
PEAK_MB=$(( PEAK_MB * 11 / 10 ))   # +10 %: the peak varies between runs (5.4-7.3 GB in route_p2)
NPAR=$(( MEM_GB * 1024 * 8 / 10 / PEAK_MB )); (( NPAR > P )) && NPAR=$P; (( NPAR < 1 )) && NPAR=1
say "Parallel judging runs" "up to $NPAR at once (one per P core, peak ${PEAK_MB} MB each, 80 % of memory)"
MACOS=$(sw_vers -productVersion)
[[ $MACOS == $REF_MACOS ]] && ok "macOS" "$MACOS" || warn "macOS" "$MACOS (reference $REF_MACOS)"

# ---------------------------------------------------------------------------------------------
section "Command Line Tools, Homebrew, PATH"
if xcode-select -p >/dev/null 2>&1; then
  CLT=$(pkgutil --pkg-info=com.apple.pkg.CLTools_Executables 2>/dev/null | awk '/version:/{print $2}')
  [[ $CLT == $REF_CLT ]] && ok "Command Line Tools" "$CLT" || warn "Command Line Tools" "${CLT:-Xcode} (reference $REF_CLT; not pinned)"
else
  (( CHECK )) && { fail "Command Line Tools" "missing (xcode-select --install)"; exit 1; }
  xcode-select --install || true
  fail "Command Line Tools" "installer opened; finish it, then re-run this script"; exit 1
fi
BREW=/opt/homebrew/bin/brew
if [[ ! -x $BREW ]]; then
  fail "Homebrew" "missing. Install it (asks for your password), then re-run:"
  print '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  exit 1
fi
BV=$($BREW --version | awk 'NR==1{print $2}')
[[ $BV == $REF_BREW ]] && ok "Homebrew" "$BV" || warn "Homebrew" "$BV (reference $REF_BREW; not pinned)"
# PATH: only if a fresh login shell can't find brew. Homebrew's own installer doesn't edit
# ~/.zprofile; the .pkg installer writes /etc/paths.d/homebrew instead. Either is enough.
LOGIN_BREW=$(env -i HOME=$HOME USER=$USER TERM=dumb /bin/zsh -lc 'command -v brew' 2>/dev/null || true)
if [[ $LOGIN_BREW == $BREW ]]; then
  ok "PATH" "a login shell finds $BREW"
elif (( CHECK )); then
  would "PATH" "add 'eval \"\$($BREW shellenv)\"' to ~/.zprofile"
else
  cp -p ~/.zprofile ~/.zprofile.bak-$(date +%Y%m%d%H%M%S) 2>/dev/null || true
  print -l '' '# >>> node60 setup-workstation >>>' "eval \"\$($BREW shellenv)\"" '# <<< node60 setup-workstation <<<' >> ~/.zprofile
  changed "PATH" "added Homebrew's shellenv to ~/.zprofile (backup beside it); open a new terminal"
fi
eval "$($BREW shellenv)"   # for the rest of this run
export HOMEBREW_NO_ENV_HINTS=1

# ---------------------------------------------------------------------------------------------
section "Homebrew packages"
ver_of() { $BREW list --versions $1 2>/dev/null | awk '{print $NF}' | sed 's/_[0-9]*$//'; }
ref_of() { case $1 in uv) print $REF_UV;; node) print $REF_NODE;; gh) print $REF_GH;; git-lfs) print $REF_GIT_LFS;; d2) print $REF_D2;; *) print "";; esac; }
for f in ${=BREW_FORMULAE}; do
  v=$(ver_of $f)
  if [[ -z $v ]]; then
    do_or_would $f brew install $f && changed $f "installed $(ver_of $f)" || true
    v=$(ver_of $f)
  fi
  [[ -z $v ]] && continue
  r=$(ref_of $f)
  if [[ -z $r || $v == $r ]]; then ok $f "$v"; else warn $f "$v (reference $r; Homebrew can't install an old version)"; fi
done
if (( EXTRAS )); then
  for f in ${=BREW_EXTRA_FORMULAE}; do
    [[ -n $(ver_of $f) ]] && ok $f "$(ver_of $f) (extra)" || { do_or_would $f brew install $f && changed $f "installed (extra)" || true; }
  done
  for c in ${=BREW_EXTRA_CASKS}; do
    $BREW list --cask $c >/dev/null 2>&1 && ok $c "cask (extra)" || { do_or_would $c brew install --cask $c && changed $c "installed cask (extra)" || true; }
  done
fi
NPMV=$(npm --version 2>/dev/null || true)
[[ $NPMV == $REF_NPM ]] && ok "npm" "$NPMV" || warn "npm" "${NPMV:-missing} (reference $REF_NPM, comes with node)"

# ---------------------------------------------------------------------------------------------
section "KiCad $KICAD_VERSION"
kicad_ver() { defaults read $KICAD_APP/Contents/Info.plist CFBundleShortVersionString 2>/dev/null || true; }
KV=$(kicad_ver)
if [[ -z $KV ]]; then
  CASKV=$($BREW info --cask --json=v2 kicad 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["casks"][0]["version"])' 2>/dev/null || true)
  if [[ $CASKV == $KICAD_VERSION ]]; then
    do_or_would "KiCad" brew install --cask kicad && changed "KiCad" "installed cask kicad $KICAD_VERSION" || true
  elif (( CHECK )); then
    would "KiCad" "download $KICAD_DMG_URL, check sha256, copy to /Applications/KiCad"
  else
    # The cask has moved past the pin: install the same dmg the cask used, checked by hash.
    T=$(mktemp -d); print "    \$ curl -L -o $T/kicad.dmg $KICAD_DMG_URL"
    curl -fL --progress-bar -o $T/kicad.dmg $KICAD_DMG_URL
    [[ $(shasum -a 256 $T/kicad.dmg | awk '{print $1}') == $KICAD_DMG_SHA256 ]] || { fail "KiCad" "dmg sha256 mismatch"; exit 1; }
    hdiutil attach -quiet -nobrowse -readonly -mountpoint $T/mnt $T/kicad.dmg
    ditto $T/mnt/KiCad /Applications/KiCad
    hdiutil detach -quiet $T/mnt; rm -rf $T
    changed "KiCad" "installed $KICAD_VERSION from the dmg (cask is at ${CASKV:-?})"
  fi
  KV=$(kicad_ver)
fi
if [[ -n $KV ]]; then
  [[ $KV == $KICAD_VERSION ]] && ok "KiCad.app" "$KV" || fail "KiCad.app" "$KV, not $KICAD_VERSION (brew uninstall --cask kicad, then re-run)"
fi
if [[ -x $KICAD_APP/Contents/MacOS/kicad-cli ]]; then
  if [[ $(command -v kicad-cli) == /opt/homebrew/bin/kicad-cli ]]; then ok "kicad-cli" "$(kicad-cli --version) (/opt/homebrew/bin)"
  elif (( CHECK )); then would "kicad-cli" "ln -s $KICAD_APP/Contents/MacOS/kicad-cli /opt/homebrew/bin/kicad-cli"
  else ln -sf $KICAD_APP/Contents/MacOS/kicad-cli /opt/homebrew/bin/kicad-cli; changed "kicad-cli" "linked into /opt/homebrew/bin, as the cask does"; fi
fi
if [[ -x $KICAD_PY ]] && $KICAD_PY -c 'import pcbnew' >/dev/null 2>&1; then ok "KiCad Python" "$($KICAD_PY --version 2>&1) with pcbnew"
else fail "KiCad Python" "$KICAD_PY can't import pcbnew"; fi

# ---------------------------------------------------------------------------------------------
section "GitHub and repositories (~/Dev)"
if gh auth status >/dev/null 2>&1; then
  ok "gh auth" "$(gh api user -q .login 2>/dev/null)"
else
  fail "gh auth" "not logged in: run 'gh auth login' (HTTPS, browser), then re-run (dropout-vendor-docs is private)"
  (( CHECK )) || exit 1
fi
if git config --global filter.lfs.process >/dev/null; then ok "git-lfs hooks" "in ~/.gitconfig"
else do_or_would "git-lfs hooks" git lfs install && changed "git-lfs hooks" "git lfs install (filters in ~/.gitconfig)" || true; fi
GN=$(git config --global user.name || true); GE=$(git config --global user.email || true)
[[ -n $GN && -n $GE ]] && ok "git identity" "$GN" || warn "git identity" "set git config --global user.name / user.email (handbook ch. 07 step 5; you)"
VL=$HOME/.local/share/dropout/vendor-logins   # never read here: only its presence and mode
if [[ -f $VL ]]; then
  [[ $(stat -f %Lp $VL) == 600 ]] && ok "vendor-logins" "present, mode 600" || warn "vendor-logins" "mode $(stat -f %Lp $VL); chmod 600 $VL"
else warn "vendor-logins" "missing: you create $VL (mode 600), handbook ch. 07 Credentials"; fi
# Handbook ch. 07 step 8: the API keys reach every shell, and Claude, through ~/.zshrc (user, 2026-11-03: the script adds it)
if grep -q 'scripts/vendor-env.sh' ~/.zshrc 2>/dev/null; then ok "vendor-env in ~/.zshrc" "API keys reach shells"
elif [[ ! -f $VL ]]; then warn "vendor-env in ~/.zshrc" "not added until $VL exists; re-run then"
elif (( CHECK )); then would "vendor-env in ~/.zshrc" "add 'eval \"\$(\"\$HOME/Dev/dropout-kicad-library/scripts/vendor-env.sh\")\"' to ~/.zshrc"
else
  [[ -f ~/.zshrc ]] && cp -p ~/.zshrc ~/.zshrc.bak-$(date +%Y%m%d%H%M%S)
  print -l '' '# >>> node60 setup-workstation: distributor API keys (handbook ch. 07) >>>' \
    'eval "$("$HOME/Dev/dropout-kicad-library/scripts/vendor-env.sh")"' \
    '# <<< node60 setup-workstation <<<' >> ~/.zshrc
  changed "vendor-env in ~/.zshrc" "added (backup beside it); open a new terminal or restart the Claude app"
fi
(( CHECK )) || mkdir -p $DEV
repo_state() {   # name dir
  local d=$2 br sha dirty url
  url=$(git -C $d remote get-url origin 2>/dev/null || echo "?")
  br=$(git -C $d branch --show-current); sha=$(git -C $d rev-parse --short HEAD)
  dirty=$(git -C $d status --porcelain | wc -l | tr -d ' ')
  say "$1" "ok  ${br:-detached}@$sha, $dirty uncommitted, $url"
}
for line in ${(f)REPOS}; do
  name=${line%%|*} slug=${line#*|}
  if [[ -d $DEV/$name/.git ]]; then repo_state $name $DEV/$name
  elif [[ -e $DEV/$name ]]; then fail $name "$DEV/$name exists and isn't a git checkout"
  else
    extra=(); [[ $name == node60-hw ]] && extra=(-- --recurse-submodules)
    do_or_would $name gh repo clone $slug $DEV/$name $extra && changed $name "cloned $slug" || true
  fi
done
if [[ -d $DEV/node60-hw/.git ]]; then
  s=$(git -C $DEV/node60-hw submodule status lib/dropout-kicad-library 2>/dev/null || true)
  if [[ $s == -* ]]; then do_or_would "node60-hw submodule" git -C $DEV/node60-hw submodule update --init && changed "node60-hw submodule" "initialised lib/dropout-kicad-library" || true
  else ok "node60-hw submodule" "lib/dropout-kicad-library at ${${s## }:0:9}"; fi
fi

# ---------------------------------------------------------------------------------------------
section "KiCadRoutingTools ($KRT)"
# Not pinned: KRT tracks origin/main (user, 2026-11-04). A new clone is at origin/main; an existing
# checkout is reported, and moved only with --update-krt (fast-forward, on main, clean).
krt_ver() { sed -n 's/^version *= *"\(.*\)"/\1/p' $KRT/rust_router/Cargo.toml 2>/dev/null | head -1; }
if [[ ! -d $KRT/.git ]]; then
  do_or_would "KRT" git clone -q $KRT_URL $KRT && changed "KRT" "cloned origin/main at $(git -C $KRT rev-parse --short=8 HEAD)" || true
elif (( UPDATE_KRT )); then
  B=$(git -C $KRT branch --show-current); H0=$(git -C $KRT rev-parse HEAD)
  if [[ $B != main || -n $(git -C $KRT status --porcelain) ]]; then warn "KRT update" "not on a clean main ($B); left alone"
  elif (( CHECK )); then would "KRT update" "git -C $KRT pull --ff-only"
  else
    git -C $KRT pull -q --ff-only && H1=$(git -C $KRT rev-parse HEAD)
    [[ $H1 == $H0 ]] && ok "KRT update" "already at origin/main" || changed "KRT update" "fast-forwarded ${H0:0:8} -> ${H1:0:8}"
  fi
fi
if [[ -d $KRT/.git ]]; then
  H=$(git -C $KRT rev-parse HEAD)
  behind=$(git -C $KRT rev-list --count HEAD..origin/main 2>/dev/null || print '?')
  info="$(git -C $KRT describe --tags 2>/dev/null || print ${H:0:8}), $(git -C $KRT branch --show-current || true), crate $(krt_ver)"
  if [[ $behind == 0 ]]; then ok "KRT commit" "${H:0:8} = origin/main as last fetched ($info)"
  else say "KRT commit" "${H:0:8}, $behind behind origin/main as last fetched ($info; --update-krt to fast-forward)"; fi
  [[ $H == $REF_KRT_COMMIT ]] || say "" "(the reference run used ${REF_KRT_COMMIT:0:8}; information only)"
fi

section "KRT Python ($VENV)"
UVV=$(uv --version | awk '{print $2}')
if uv python find $KRT_PYTHON >/dev/null 2>&1; then ok "uv CPython" "$KRT_PYTHON"
else do_or_would "uv CPython" uv python install $KRT_PYTHON && changed "uv CPython" "installed $KRT_PYTHON" || true; fi
if [[ ! -x $VENV/bin/python ]]; then
  do_or_would "krt-venv" uv venv -q --python $KRT_PYTHON $VENV && changed "krt-venv" "created ($KRT_PYTHON)" || true
fi
if [[ -x $VENV/bin/python ]]; then
  PV=$($VENV/bin/python -c 'import platform; print(platform.python_version())')
  [[ $PV == $KRT_PYTHON ]] && ok "krt-venv Python" "$PV" || fail "krt-venv Python" "$PV, not $KRT_PYTHON (rm -rf $VENV and re-run)"
  WANT=$(grep -v -E '^\s*(#|$)' $HERE/workstation/krt-requirements.txt | tr 'A-Z' 'a-z' | sort)
  have() { uv pip freeze -q --python $VENV/bin/python 2>/dev/null | tr 'A-Z' 'a-z' | sort; }
  if [[ $(have) == $WANT ]]; then ok "krt-venv packages" "${(j:, :)${(f)WANT}}"
  else
    say "krt-venv packages" "have: ${(j:, :)${(f)$(have)}}"
    do_or_would "krt-venv packages" uv pip sync -q --python $VENV/bin/python $HERE/workstation/krt-requirements.txt \
      && changed "krt-venv packages" "synced to krt-requirements.txt" || true
  fi
fi

section "KRT router binary"
# The published prebuilt whose version matches the checkout's crate (KRT's own startup guard), from
# build_router.py. No cargo: if no prebuilt matches (crate ahead of the last release), that fails here.
SO=$KRT/rust_router/grid_router.so
so_ver() { (cd $KRT && $VENV/bin/python -c 'import sys; sys.path.insert(0, "rust_router"); import grid_router; print(grid_router.__version__)' 2>/dev/null) || true; }
if [[ -d $KRT/.git && -x $VENV/bin/python ]]; then
  WV=$(krt_ver); HV=$(so_ver)
  if [[ -n $HV && $HV == $WV ]]; then ok "grid_router.so" "$HV, matches the crate (sha256 $(shasum -a 256 $SO | cut -c1-12))"
  else
    [[ -n $HV ]] && say "grid_router.so" "$HV, crate is $WV"
    if (( CHECK )); then would "grid_router.so" "(cd $KRT && python3 build_router.py)"
    else
      print "    \$ (cd $KRT && $VENV/bin/python build_router.py)"
      (cd $KRT && $VENV/bin/python build_router.py) || true
      HV=$(so_ver)
      [[ -n $HV && $HV == $WV ]] && changed "grid_router.so" "installed prebuilt $HV (sha256 $(shasum -a 256 $SO | cut -c1-12))" \
        || fail "grid_router.so" "${HV:-none} after build_router.py, crate $WV: no matching prebuilt yet (that needs cargo)"
    fi
  fi
fi

# ---------------------------------------------------------------------------------------------
section "Library tools (klt-venv, the library's own setup)"
ST=$DEV/dropout-kicad-library/scripts/setup_tools.sh
if [[ -x $ST || -f $ST ]]; then
  if (( CHECK )); then out=$(bash $ST --check 2>&1) && ok "setup_tools.sh --check" "all present" || warn "setup_tools.sh --check" "something missing (see below)"
  else out=$(bash $ST 2>&1) && ok "setup_tools.sh" "done" || fail "setup_tools.sh" "failed (see below)"; fi
  print -- "$out" | grep -v '^$' | sed 's/^/      /'
else warn "setup_tools.sh" "not in $DEV/dropout-kicad-library (klt-venv, used by part_heights.py, not set up)"; fi

section "Claude Code"
if command -v claude >/dev/null; then
  CV=$(claude --version 2>/dev/null | awk '{print $1}')
  [[ $CV == $REF_CLAUDE ]] && ok "claude" "$CV" || warn "claude" "$CV (reference $REF_CLAUDE; updates itself)"
  PL=$(claude plugin list 2>/dev/null || true)
  for line in ${(f)PLUGINS}; do
    id=${line%%|*} rest=${line#*|}; mrepo=${rest%%|*} rver=${rest#*|}
    pv=$(print -- "$PL" | awk -v id="$id" '$0 ~ id {f=1; next} f && /Version:/ {print $2; exit}')
    if [[ -n $pv ]]; then
      [[ $pv == $rver ]] && ok "${id%@*} plugin" "$pv" || warn "${id%@*} plugin" "$pv (reference $rver; follows its repo)"
    elif (( ! PLUGINS_ON )); then say "${id%@*} plugin" "not installed (--no-plugins)"
    elif (( CHECK )); then would "${id%@*} plugin" "claude plugin marketplace add $mrepo; claude plugin install $id"
    else
      print -- "    \$ claude plugin marketplace add $mrepo && claude plugin install $id"
      claude plugin marketplace add $mrepo >/dev/null && claude plugin install $id >/dev/null \
        && changed "${id%@*} plugin" "installed $id (user scope)" || fail "${id%@*} plugin" "install failed"
    fi
  done
else warn "claude" "not installed: curl -fsSL https://claude.ai/install.sh | bash, or the desktop app"; fi
say "ee-skills" "add $DEV/ee-skills/skills/pcb-placement to a session as a folder when the skill needs it"

if [[ $HOME != /Users/karl ]]; then
  warn "home folder" "$HOME is not /Users/karl: set KRT_PY=$VENV/bin/python for gate.py (plan.json's krt_python is absolute); nudge.sh and route_open.sh hard-code /Users/karl"
fi

# =============================================================================================
section "Verify (changes nothing in the repos: works on a git-archive export in a temp folder)"
N60=$DEV/node60-hw
[[ -d $N60/.git ]] || { fail "verify" "no $N60"; }
W=$(mktemp -d -t node60-verify)
trap 'rm -rf $W' EXIT
# export_commit SHA DEST URL CLONE...: git-archive SHA into DEST from the first local clone that has it,
# else fetch just that commit from URL into a scratch repo inside the temp folder (never into a repo).
export_commit() {
  local sha=$1 dest=$2 url=$3 d; shift 3
  mkdir -p $dest
  for d in "$@"; do
    [[ -d $d ]] && git -C $d cat-file -e "$sha^{commit}" 2>/dev/null && { git -C $d archive $sha | tar -x -C $dest; print -- "$d"; return 0; }
  done
  local f=$W/.fetch-${sha:0:12}
  git init -q $f && git -C $f -c credential.helper='!gh auth git-credential' fetch -q --depth 1 $url $sha 2>/dev/null \
    && git -C $f archive FETCH_HEAD | tar -x -C $dest && { print -- "GitHub (fetched into the temp folder)"; return 0; }
  return 1
}
if [[ -d $N60/.git ]]; then
  [[ -z $REF ]] && REF=$REF_JUDGE_COMMIT
  C=$(git -C $N60 rev-parse -q --verify "$REF^{commit}" 2>/dev/null || print -- $REF)
  if from=$(export_commit $C $W https://github.com/karlTbowers/node60-hw.git $N60); then
    ok "node60-hw ${C:0:8}" "($REF) from $from"
  else fail "node60-hw ${C:0:8}" "$REF not found locally or on GitHub"; fi
  G=$(git -C $N60 ls-tree $C lib/dropout-kicad-library 2>/dev/null | awk '{print $3}')
  [[ -z $G ]] && G=$(git -C $W/.fetch-${C:0:12} ls-tree FETCH_HEAD lib/dropout-kicad-library 2>/dev/null | awk '{print $3}')
  if [[ -n $G ]] && from=$(export_commit $G $W/lib/dropout-kicad-library https://github.com/karlTbowers/dropout-kicad-library.git \
       $N60/lib/dropout-kicad-library $DEV/dropout-kicad-library); then ok "library ${G:0:8}" "from $from"
  else fail "library ${G:0:8}" "submodule commit not found"; fi

  out=$($KICAD_PY -c 'import pcbnew; print(pcbnew.GetBuildVersion())' 2>&1 | tail -1) && ok "pcbnew" "imports in KiCad's Python ($out)" || fail "pcbnew" "$out"
  out=$(cd $KRT && $VENV/bin/python -c 'import sys; sys.path.insert(0, "rust_router"); import grid_router, numpy, scipy, shapely; print(grid_router.__version__, numpy.__version__, scipy.__version__, shapely.__version__)' 2>&1 | tail -1) \
    && ok "krt-venv imports" "grid_router, numpy, scipy, shapely = $out" || fail "krt-venv imports" "$out"

  (cd $W && kicad-cli pcb drc --exit-code-violations --severity-error --schematic-parity --output $W/drc.rpt node60.kicad_pcb >/dev/null 2>&1) \
    && ok "DRC (CI's check)" "kicad-cli pcb drc --exit-code-violations --severity-error --schematic-parity: exit 0" \
    || { fail "DRC (CI's check)" "violations:"; grep -E '^\[|errors|violations' $W/drc.rpt | head -20 | sed 's/^/      /'; }

  PR=$W/placement/2026-11-02-bars/rules/prove_rules.py
  if [[ -f $PR ]]; then
    out=$(cd $W && $KICAD_PY $PR node60.kicad_pcb 2>&1 | grep -E '^(PASS|FAIL)|cases pass' ); rc=$?
    last=$(print -- "$out" | tail -1)
    (( rc == 0 )) && [[ $last =~ '^([0-9]+) of ([0-9]+) cases pass' && $match[1] == $match[2] ]] && ok "prove_rules.py" "$last" \
      || { fail "prove_rules.py" "$last"; print -- "$out" | grep FAIL | sed 's/^/      /'; }
  else warn "prove_rules.py" "not at $REF"; fi

  # The handbook's own checks (ch. 07 step 11) beyond setup_tools.sh --check, on the library checkout as it is.
  LIB=$DEV/dropout-kicad-library
  if [[ -f $LIB/scripts/distributor_lookup.py ]]; then
    eval "$($LIB/scripts/vendor-env.sh 2>/dev/null)" 2>/dev/null || true
    python3 $LIB/scripts/distributor_lookup.py S32K344EHT1MMMST >/dev/null 2>&1 && ok "distributor_lookup.py" "S32K344EHT1MMMST found" \
      || warn "distributor_lookup.py" "failed (API keys from vendor-logins, or the network)"
  fi
  if [[ -x $HOME/.cache/dropout/klt-venv/bin/python && -f $LIB/scripts/klc_check.py ]]; then
    out=$(cd $LIB && $HOME/.cache/dropout/klt-venv/bin/python scripts/klc_check.py 2>&1); rc=$?
    (( rc == 0 )) && ok "klc_check.py" "no FAIL in $LIB ($(git -C $LIB branch --show-current))" \
      || warn "klc_check.py" "exit $rc on $LIB as checked out: $(print -- "$out" | grep -c '^FAIL') FAIL"
  fi

  JR=$W/placement/2026-11-02-bars/judge_route.sh
  JBLOB=$(git hash-object $JR 2>/dev/null)   # before any patching: the blob id is the same on every machine
  if (( JUDGE )) && [[ -f $JR ]]; then
    [[ -z $JOUT ]] && JOUT=$DEV/node60-judge-runs/$(hostname -s)-$(date +%Y%m%d-%H%M)
    mkdir -p ${JOUT:h}
    say "judging run" "$JOUT (7-36 min) ..."
    # --krt-at reference (default): route with the reference run's KRT, exported into the temp folder with
    # its router binary, never moving ~/Dev/KiCadRoutingTools (other sessions use it, and something pulls
    # it nightly). Then the result must equal the reference. --krt-at live: the checkout as it is.
    KX=$KRT RUN_KRT=$(git -C $KRT rev-parse HEAD 2>/dev/null)
    if [[ $KRT_AT == reference ]]; then
      KX=$W/krt RUN_KRT=$REF_KRT_COMMIT
      RTAG=${REF_KRT_ROUTER%% *} RSHA=${REF_KRT_ROUTER##* }
      if from=$(export_commit $REF_KRT_COMMIT $KX $KRT_URL $KRT); then
        if [[ $(shasum -a 256 $SO 2>/dev/null | awk '{print $1}') == $RSHA ]]; then cp $SO $KX/rust_router/
        else (cd $KX && $VENV/bin/python build_router.py --tag $RTAG >/dev/null 2>&1) || true; fi
        if [[ $(shasum -a 256 $KX/rust_router/grid_router.so 2>/dev/null | awk '{print $1}') == $RSHA ]]; then
          sed -i '' "s#^KRT=~/Dev/KiCadRoutingTools\$#KRT=$KX#" $JR
          grep -q "^KRT=$KX\$" $JR && ok "KRT for the run" "reference ${REF_KRT_COMMIT:0:8} (from $from), router $RTAG" \
            || { fail "KRT for the run" "couldn't point judge_route.sh at the copy"; KX=$KRT RUN_KRT=$(git -C $KRT rev-parse HEAD); }
        else fail "KRT for the run" "no $RTAG router binary for the copy"; KX=$KRT RUN_KRT=$(git -C $KRT rev-parse HEAD); fi
      else fail "KRT for the run" "couldn't export ${REF_KRT_COMMIT:0:8}"; KX=$KRT RUN_KRT=$(git -C $KRT rev-parse HEAD); fi
    else ok "KRT for the run" "live checkout ${RUN_KRT:0:8}"; fi
    mkdir -p $JOUT
    { print "host\t$(hostname -s) $(sysctl -n hw.model) $(sysctl -n machdep.cpu.brand_string), $P P + $E E cores, $MEM_GB GB, macOS $MACOS"
      print "node60_commit\t$C"
      print "judge\t$JBLOB (git blob of placement/2026-11-02-bars/judge_route.sh)"
      print "krt_commit\t$RUN_KRT ($KRT_AT)"
      print "grid_router\t$(shasum -a 256 $KX/rust_router/grid_router.so | cut -c1-12)"
      print "kicad\t$KV"; print "started\t$(date '+%Y-%m-%d %H:%M:%S')"; } > $JOUT/versions.txt
    T0=$(date +%s)
    (cd $W && KRT_PY=$VENV/bin/python zsh $JR node60.kicad_pcb $JOUT >/dev/null 2>&1) || true
    T1=$(date +%s)
    cp $W/placement/2026-11-02-bars/rules/perf_report.py $JOUT/ 2>/dev/null || true
    PERF=$W/placement/2026-11-02-bars/rules/perf_report.py
    if [[ -f $JOUT/rules.json ]]; then
      # Same commit, same KRT, same inputs: the same open nets, and a blocking count within max(2, 1 %).
      # KRT is not bit-for-bit repeatable: four runs on the Air gave 330, 329, 330, 329 (one clearance item).
      cmp_out=$(python3 - $JOUT/rules.json $HERE/workstation/reference/rules.json <<'PY'
import json, sys
a, r = (json.load(open(p)) for p in sys.argv[1:])
sa, sr = set(a["open_nets"]), set(r["open_nets"])
tol = max(2, round(0.01 * r["blocking"]))
same = abs(a["blocking"] - r["blocking"]) <= tol and sa == sr
d = [f"blocking {a['blocking']} (reference {r['blocking']}, within {tol} passes)", f"{len(sa)} open nets (reference {len(sr)})"]
if sa - sr: d.append("open only here: " + ", ".join(sorted(sa - sr)))
if sr - sa: d.append("open only in the reference: " + ", ".join(sorted(sr - sa)))
for k in sorted(set(a["other_errors"]) | set(r["other_errors"])):
    x, y = a["other_errors"].get(k, 0), r["other_errors"].get(k, 0)
    if x != y: d.append(f"{k} {x} (reference {y})")
print(("SAME " if same else "DIFF ") + "; ".join(d))
PY
)
      say "judging run" "$(( T1 - T0 )) s wall"
      if [[ $C != ${REF_JUDGE_COMMIT}* || $RUN_KRT != $REF_KRT_COMMIT ]]; then
        warn "judging vs reference" "node60 ${C:0:8} + KRT ${RUN_KRT:0:8}, the reference ${REF_JUDGE_COMMIT:0:8} + ${REF_KRT_COMMIT:0:8}: information only (${cmp_out#* })"
      elif [[ $cmp_out == SAME* ]]; then ok "judging vs reference" "matches: ${cmp_out#SAME }"
      else fail "judging vs reference" "${cmp_out#DIFF }"; fi
      [[ -f $PERF ]] && python3 $PERF $JOUT $HERE/workstation/reference --md $JOUT/perf.md >/dev/null 2>&1 \
        && { say "perf_report.py" "this run vs the reference (left: this machine):"; sed 's/^/      /' $JOUT/perf.md | head -40; }
    else fail "judging run" "no rules.json in $JOUT (see $JOUT/chain.log)"; fi
  elif (( JUDGE )); then warn "judging run" "no judge_route.sh at $REF"; fi
fi

# =============================================================================================
section "Summary"
if (( ${#CHANGES} )); then print "  Changed:"; print -l -- "    "${^CHANGES}; else print "  Changed nothing."; fi
(( ${#WARNS} )) && { print "  Warnings:"; print -l -- "    "${^WARNS}; }
if (( ${#FAILS} )); then print "  FAILED:"; print -l -- "    "${^FAILS}; exit 1; fi
print "  All checks passed."
