#!/bin/bash
# QuickIce Hydrate-Interface-Custom Molecule-Ion Workflow
# Generates a hydrate structure, creates ice-water interface,
# inserts custom molecules and NaCl ions
#
# Usage: ./scripts/hydrate-interface-custom-ion.sh [OPTIONS]
#
# Required:
#   --custom-gro PATH    Path to custom molecule .gro file
#   --custom-itp PATH    Path to custom molecule .itp file
#
# Optional:
#   --ion-conc FLOAT     Ion concentration in mol/L (default: 0.15)
#   --custom-count INT   Number of custom molecules for random placement (default: 5)
#   --temperature FLOAT  Temperature in K (default: 260)
#   --pressure FLOAT     Pressure in MPa (default: 0.1)
#   --lattice-type TYPE  Hydrate lattice: sI, sII, sH (default: sI)
#   --guest TYPE         Guest molecule: CH4, THF (default: CH4)
#   --output DIR         Output directory (default: hydrate-custom-ion-output)
#   -h, --help           Show this help message
#
# Example:
#   ./scripts/hydrate-interface-custom-ion.sh \
#     --custom-gro quickice/data/custom/etoh.gro \
#     --custom-itp quickice/data/custom/etoh.itp \
#     --ion-conc 0.3

set -e

# --- Default variable assignments ---
CUSTOM_GRO=""
CUSTOM_ITP=""
ION_CONC=0.15
CUSTOM_COUNT=5
TEMPERATURE=260
PRESSURE=0.1
LATTICE_TYPE="sI"
GUEST="CH4"
OUTPUT_DIR="hydrate-custom-ion-output"

# --- Parse flags ---
while [ $# -gt 0 ]; do
    case "$1" in
        --custom-gro)
            shift
            if [ -z "$1" ]; then echo "ERROR: --custom-gro requires a PATH argument"; exit 1; fi
            CUSTOM_GRO="$1"
            ;;
        --custom-itp)
            shift
            if [ -z "$1" ]; then echo "ERROR: --custom-itp requires a PATH argument"; exit 1; fi
            CUSTOM_ITP="$1"
            ;;
        --ion-conc)
            shift
            if [ -z "$1" ]; then echo "ERROR: --ion-conc requires a FLOAT argument"; exit 1; fi
            ION_CONC="$1"
            ;;
        --custom-count)
            shift
            if [ -z "$1" ]; then echo "ERROR: --custom-count requires an INT argument"; exit 1; fi
            CUSTOM_COUNT="$1"
            ;;
        --temperature)
            shift
            if [ -z "$1" ]; then echo "ERROR: --temperature requires a FLOAT argument"; exit 1; fi
            TEMPERATURE="$1"
            ;;
        --pressure)
            shift
            if [ -z "$1" ]; then echo "ERROR: --pressure requires a FLOAT argument"; exit 1; fi
            PRESSURE="$1"
            ;;
        --lattice-type)
            shift
            if [ -z "$1" ]; then echo "ERROR: --lattice-type requires a TYPE argument"; exit 1; fi
            LATTICE_TYPE="$1"
            ;;
        --guest)
            shift
            if [ -z "$1" ]; then echo "ERROR: --guest requires a TYPE argument"; exit 1; fi
            GUEST="$1"
            ;;
        --output)
            shift
            if [ -z "$1" ]; then echo "ERROR: --output requires a DIR argument"; exit 1; fi
            OUTPUT_DIR="$1"
            ;;
        -h|--help)
            echo "Usage: ./scripts/hydrate-interface-custom-ion.sh [OPTIONS]"
            echo ""
            echo "QuickIce Hydrate-Interface-Custom Molecule-Ion Workflow"
            echo "Generates a hydrate structure, creates ice-water interface,"
            echo "inserts custom molecules and NaCl ions."
            echo ""
            echo "Required:"
            echo "  --custom-gro PATH      Path to custom molecule .gro file"
            echo "  --custom-itp PATH      Path to custom molecule .itp file"
            echo ""
            echo "Optional:"
            echo "  --ion-conc FLOAT       Ion concentration in mol/L (default: 0.15)"
            echo "  --custom-count INT     Number of custom molecules (default: 5)"
            echo "  --temperature FLOAT    Temperature in K (default: 260)"
            echo "  --pressure FLOAT       Pressure in MPa (default: 0.1)"
            echo "  --lattice-type TYPE    Hydrate lattice: sI, sII, sH (default: sI)"
            echo "  --guest TYPE           Guest molecule: CH4, THF (default: CH4)"
            echo "  --output DIR           Output directory (default: hydrate-custom-ion-output)"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Example:"
            echo "  ./scripts/hydrate-interface-custom-ion.sh \\"
            echo "    --custom-gro quickice/data/custom/etoh.gro \\"
            echo "    --custom-itp quickice/data/custom/etoh.itp \\"
            echo "    --ion-conc 0.3"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Run with --help for usage information."
            exit 1
            ;;
    esac
    shift
done

# --- Validate required arguments ---
if [ -z "$CUSTOM_GRO" ]; then
    echo "ERROR: --custom-gro is required"
    echo "Run with --help for usage information."
    exit 1
fi
if [ -z "$CUSTOM_ITP" ]; then
    echo "ERROR: --custom-itp is required"
    echo "Run with --help for usage information."
    exit 1
fi

# --- Validate files exist ---
if [ ! -f "$CUSTOM_GRO" ]; then
    echo "ERROR: Custom GRO file not found: $CUSTOM_GRO"
    exit 1
fi
if [ ! -f "$CUSTOM_ITP" ]; then
    echo "ERROR: Custom ITP file not found: $CUSTOM_ITP"
    exit 1
fi

# --- Print configuration summary ---
echo "=== QuickIce Hydrate-Interface-Custom Molecule-Ion Workflow ==="
echo ""
echo "Configuration:"
echo "  Temperature:       ${TEMPERATURE} K"
echo "  Pressure:          ${PRESSURE} MPa"
echo "  Hydrate lattice:   ${LATTICE_TYPE}"
echo "  Guest molecule:    ${GUEST}"
echo "  Custom molecule:   ${CUSTOM_GRO} / ${CUSTOM_ITP}"
echo "  Custom count:      ${CUSTOM_COUNT}"
echo "  Ion concentration: ${ION_CONC} mol/L"
echo "  Output directory:  ${OUTPUT_DIR}"
echo ""

# --- Construct and run the pipeline command ---
echo "=== Running QuickIce pipeline ==="
echo ""

CMD="python -m quickice --hydrate --lattice-type ${LATTICE_TYPE} --guest ${GUEST} --interface --mode slab --box-x 5.0 --box-y 5.0 --box-z 10.0 --ice-thickness 3.0 --water-thickness 4.0 --custom-gro ${CUSTOM_GRO} --custom-itp ${CUSTOM_ITP} --custom-placement random --custom-count ${CUSTOM_COUNT} --ion-concentration ${ION_CONC} --ion-source custom --gromacs --no-diagram --output ${OUTPUT_DIR} --temperature ${TEMPERATURE} --pressure ${PRESSURE}"

echo "Command:"
echo "  ${CMD}"
echo ""

eval $CMD
PIPELINE_EXIT=$?

if [ $PIPELINE_EXIT -ne 0 ]; then
    echo ""
    echo "ERROR: Pipeline exited with code ${PIPELINE_EXIT}"
    exit $PIPELINE_EXIT
fi

# --- Print summary ---
echo ""
echo "=== Summary ==="
echo "Pipeline completed successfully."
echo ""
echo "Output files in ${OUTPUT_DIR}/:"
if [ -d "$OUTPUT_DIR" ]; then
    ls -la "$OUTPUT_DIR"/ 2>/dev/null || echo "  (directory listing not available)"
fi
echo ""
echo "The GROMACS files (.gro, .top, .itp) are ready for simulation."
echo "Next steps: Run 'gmx grompp -f em.mdp -c <gro_file> -p <top_file>' for energy minimization."
