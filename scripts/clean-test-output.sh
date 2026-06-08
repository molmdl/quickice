#!/bin/bash
# Clean accumulated test output from tmp/ directory
# Usage: ./scripts/clean-test-output.sh [OPTIONS]
#
# Options:
#   --dry-run              Show what would be deleted without deleting
#   --include-gmx-validation  Also clean tmp/e2e-gmx-validation/ (default: preserved)
#   --stale-backups-only  Only remove GROMACS #*# backup files
#   -h, --help             Show this help message
#
# Preserved by default:
#   tmp/em.mdp             Used by grompp tests
#   tmp/e2e-gmx-validation/  Persistent grompp workspace for debugging
#
# Default mode removes ALL tmp/ contents except em.mdp and e2e-gmx-validation/.
# Stale backup mode only removes GROMACS backup files matching #*# pattern.

set -e

# --- Parse flags ---
DRY_RUN=false
INCLUDE_GMX_VALIDATION=false
STALE_BACKUPS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        --include-gmx-validation)
            INCLUDE_GMX_VALIDATION=true
            ;;
        --stale-backups-only)
            STALE_BACKUPS_ONLY=true
            ;;
        -h|--help)
            echo "Usage: ./scripts/clean-test-output.sh [OPTIONS]"
            echo ""
            echo "Clean accumulated test output from the tmp/ directory."
            echo ""
            echo "Options:"
            echo "  --dry-run                Show what would be deleted without deleting"
            echo "  --include-gmx-validation Also clean tmp/e2e-gmx-validation/ (default: preserved)"
            echo "  --stale-backups-only     Only remove GROMACS #*# backup files"
            echo "  -h, --help               Show this help message"
            echo ""
            echo "Preserved by default:"
            echo "  tmp/em.mdp               Used by grompp tests"
            echo "  tmp/e2e-gmx-validation/  Persistent grompp workspace for debugging"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $arg"
            echo "Run with --help for usage information."
            exit 1
            ;;
    esac
done

# --- Check we are in repo root ---
if [ ! -d "tmp" ]; then
    echo "ERROR: tmp/ directory not found. Run this script from the repo root."
    exit 1
fi

# --- Helper: prefix for dry-run ---
prefix() {
    if $DRY_RUN; then
        echo "[DRY RUN]"
    else
        echo ""
    fi
}

# --- Stale-backups-only mode ---
if $STALE_BACKUPS_ONLY; then
    echo "=== Cleaning stale GROMACS backup files (#*# pattern) ==="
    if $DRY_RUN; then
        echo "[DRY RUN] Scanning for stale backup files..."
    fi

    dirs_removed=0
    files_removed=0
    stale_count=0

    # Find and process #*# files
    while IFS= read -r -d '' backup_file; do
        stale_count=$((stale_count + 1))
        P=$(prefix)
        echo "${P}Removing file: $backup_file"
        if ! $DRY_RUN; then
            rm -f "$backup_file"
            files_removed=$((files_removed + 1))
        fi
    done < <(find tmp/ -name '#*#' -type f -print0 2>/dev/null)

    # Also remove empty directories left behind (but not tmp/ itself or preserved dirs)
    if ! $DRY_RUN; then
        while IFS= read -r -d '' empty_dir; do
            if [ "$empty_dir" != "tmp/" ] && [ "$empty_dir" != "tmp" ]; then
                rmdir "$empty_dir" 2>/dev/null && dirs_removed=$((dirs_removed + 1)) || true
            fi
        done < <(find tmp/ -type d -empty -print0 2>/dev/null)
    fi

    echo ""
    echo "=== Summary ==="
    if $DRY_RUN; then
        echo "[DRY RUN] Stale backup files found: $stale_count"
        echo "[DRY RUN] No files were deleted."
    else
        echo "Stale backup files removed: $stale_count"
        echo "Files removed: $files_removed"
        echo "Empty directories removed: $dirs_removed"
    fi
    exit 0
fi

# --- Default cleanup mode ---
echo "=== Cleaning tmp/ directory ==="

# Record size before cleanup (non-dry-run only)
if ! $DRY_RUN; then
    size_before=$(du -sh tmp/ 2>/dev/null | cut -f1)
fi

dirs_removed=0
files_removed=0
stale_count=0

# Process items in tmp/ directory
for item in tmp/*; do
    # Skip em.mdp (always preserved)
    if [ "$item" = "tmp/em.mdp" ]; then
        continue
    fi

    # Skip e2e-gmx-validation/ unless --include-gmx-validation
    if [ "$item" = "tmp/e2e-gmx-validation" ] && ! $INCLUDE_GMX_VALIDATION; then
        if $DRY_RUN; then
            echo "[DRY RUN] Preserving: $item/ (use --include-gmx-validation to clean)"
        fi
        continue
    fi

    P=$(prefix)

    if [ -d "$item" ]; then
        # Count stale backups in this directory before removal
        stale_in_dir=$(find "$item" -name '#*#' -type f 2>/dev/null | wc -l)
        stale_count=$((stale_count + stale_in_dir))

        # Count regular files
        regular_in_dir=$(find "$item" -type f 2>/dev/null | wc -l)
        files_removed=$((files_removed + regular_in_dir))

        echo "${P}Removing directory: $item/ (${regular_in_dir} files${stale_in_dir:+, ${stale_in_dir} stale backups})"
        if ! $DRY_RUN; then
            rm -rf "$item"
        fi
        dirs_removed=$((dirs_removed + 1))
    elif [ -f "$item" ]; then
        # Check if it's a stale backup file
        basename=$(basename "$item")
        case "$basename" in
            \#*\#)
                stale_count=$((stale_count + 1))
                echo "${P}Removing stale backup: $item"
                ;;
            *)
                echo "${P}Removing file: $item"
                ;;
        esac
        files_removed=$((files_removed + 1))
        if ! $DRY_RUN; then
            rm -f "$item"
        fi
    fi
done

# Also handle hidden items (like .nfs* files)
for item in tmp/.*; do
    # Skip . and ..
    case "$(basename "$item")" in
        .|..) continue ;;
    esac

    P=$(prefix)
    if [ -f "$item" ] || [ -d "$item" ]; then
        echo "${P}Removing hidden: $item"
        if [ -d "$item" ]; then
            files_in_dir=$(find "$item" -type f 2>/dev/null | wc -l)
            files_removed=$((files_removed + files_in_dir))
            if ! $DRY_RUN; then
                rm -rf "$item"
            fi
            dirs_removed=$((dirs_removed + 1))
        else
            files_removed=$((files_removed + 1))
            if ! $DRY_RUN; then
                rm -f "$item"
            fi
        fi
    fi
done

echo ""
echo "=== Summary ==="
if $DRY_RUN; then
    echo "[DRY RUN] Directories that would be removed: $dirs_removed"
    echo "[DRY RUN] Files that would be removed: $files_removed"
    echo "[DRY RUN]   Stale backup files (#*#): $stale_count"
    echo "[DRY RUN] No files were deleted."
    echo "[DRY RUN] Preserved: tmp/em.mdp"
    if ! $INCLUDE_GMX_VALIDATION; then
        echo "[DRY RUN] Preserved: tmp/e2e-gmx-validation/ (use --include-gmx-validation to clean)"
    fi
else
    size_after=$(du -sh tmp/ 2>/dev/null | cut -f1)
    echo "Directories removed: $dirs_removed"
    echo "Files removed: $files_removed"
    echo "  Stale backup files (#*#): $stale_count"
    echo "Size before: $size_before"
    echo "Size after:  $size_after"
    echo "Preserved: tmp/em.mdp"
    if ! $INCLUDE_GMX_VALIDATION; then
        echo "Preserved: tmp/e2e-gmx-validation/"
    fi
fi
