#!/usr/bin/env bash
set -euo pipefail

# ---------- Tunables (override via env) ----------
WORLD="${WORLD:-default}"       # auto-detects if not found
TABLE_TOP_Z="${TABLE_TOP_Z:-0.30}"
TABLE_SIZE_X="${TABLE_SIZE_X:-1.0}"
TABLE_SIZE_Y="${TABLE_SIZE_Y:-1.0}"
TABLE_THICK="${TABLE_THICK:-0.05}"  # 5 cm thick

X="${X:-0.45}"                  # forward distance of the cubes
SPACING="${SPACING:-0.08}"      # +/- Y offset
BLOCK_SIZE="${BLOCK_SIZE:-0.04}"      # 40 mm cubes
BLOCK_DROP="${BLOCK_DROP:-0.01}"      # ~1 cm drop onto table

# Idempotency: keep false so names are consistent (enables clean delete)
ALLOW_RENAME="${ALLOW_RENAME:-false}"

# Also sweep possible suffixes (old runs that used allow_renaming=true)
SWEEP_SUFFIXES="${SWEEP_SUFFIXES:-true}"   # true/false
MAX_SUFFIX="${MAX_SUFFIX:-9}"
# -------------------------------------------------

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: $1 not found"; exit 1; }; }
need gz

# Ensure a world is running and detect its name if needed
if ! gz service -l | grep -q "/world/"; then
  echo "ERROR: No Gazebo world detected. Is Gazebo running?" >&2
  exit 1
fi
if ! gz service -l | grep -q "/world/${WORLD}/create"; then
  DETECTED=$(gz service -l | sed -n 's#.*/world/\([^/]*\)/create.*#\1#p' | head -n1 || true)
  [[ -n "$DETECTED" ]] && WORLD="$DETECTED"
fi
echo "Using world: ${WORLD}"

# Choose correct gz flag style (new: --reqtype/--reptype/--req, legacy: -m/-r/-p)
USE_LONG_FLAGS=false
if gz service --help 2>/dev/null | grep -q -- '--reqtype'; then
  USE_LONG_FLAGS=true
fi

# ---------- service helpers ----------
call_create() {
  local sdf_path="$1" name="$2" x="$3" y="$4" z="$5"
  local payload
  payload=$(cat <<PBUF
sdf_filename: "$sdf_path"
name: "$name"
pose { position { x: $x y: $y z: $z } }
allow_renaming: ${ALLOW_RENAME}
PBUF
)
  if $USE_LONG_FLAGS; then
    gz service -s "/world/${WORLD}/create" \
      --reqtype gz.msgs.EntityFactory \
      --reptype gz.msgs.Boolean \
      --timeout 3000 \
      --req "$payload" >/dev/null
  else
    gz service -s "/world/${WORLD}/create" \
      -m gz.msgs.EntityFactory \
      -r gz.msgs.Boolean \
      -p "$payload" >/dev/null
  fi
}

# Remove a model by name (try symbolic enum then numeric fallback)
remove_model_once() {
  local name="$1"
  local payload_sym=$'name: "'"$name"$'"\n'"type: MODEL"
  local payload_num=$'name: "'"$name"$'"\n'"type: 2"   # 2 = MODEL
  if $USE_LONG_FLAGS; then
    gz service -s "/world/${WORLD}/remove" \
      --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean --timeout 3000 \
      --req "$payload_sym" >/dev/null 2>&1 \
    || gz service -s "/world/${WORLD}/remove" \
      --reqtype gz.msgs.Entity --reptype gz.msgs.Boolean --timeout 3000 \
      --req "$payload_num" >/dev/null 2>&1 || true
  else
    gz service -s "/world/${WORLD}/remove" \
      -m gz.msgs.Entity -r gz.msgs.Boolean -p "$payload_sym" >/dev/null 2>&1 \
    || gz service -s "/world/${WORLD}/remove" \
      -m gz.msgs.Entity -r gz.msgs.Boolean -p "$payload_num" >/dev/null 2>&1 || true
  fi
}

remove_model() {
  local base="$1"
  # remove exact name
  remove_model_once "$base"
  # optionally sweep suffixed names like base_1 ... base_9
  if [[ "$SWEEP_SUFFIXES" == "true" ]]; then
    for i in $(seq 1 "$MAX_SUFFIX"); do
      remove_model_once "${base}_${i}"
    done
  fi
}
# -------------------------------------

# ---------- write SDFs ----------
SDF_DIR=/tmp/lab06_spawn
mkdir -p "$SDF_DIR"

# Static table — center z = TABLE_TOP_Z - THICK/2 so top surface is at TABLE_TOP_Z
TABLE_SDF="${SDF_DIR}/table_${TABLE_SIZE_X}x${TABLE_SIZE_Y}x${TABLE_THICK}.sdf"
cat > "$TABLE_SDF" <<EOF
<?xml version="1.0" ?>
<sdf version="1.8">
  <model name="lab06_table">
    <static>true</static>
    <pose>0 0 0 0 0 0</pose>
    <link name="top">
      <collision name="collision">
        <geometry><box><size>${TABLE_SIZE_X} ${TABLE_SIZE_Y} ${TABLE_THICK}</size></box></geometry>
        <surface><contact/><friction/></surface>
      </collision>
      <visual name="visual">
        <geometry><box><size>${TABLE_SIZE_X} ${TABLE_SIZE_Y} ${TABLE_THICK}</size></box></geometry>
        <material>
          <ambient>0.5 0.5 0.5 1</ambient>
          <diffuse>0.55 0.55 0.55 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>
EOF

write_cube_sdf() {
  local path="$1" r="$2" g="$3" b="$4"
  cat > "$path" <<EOF
<?xml version="1.0" ?>
<sdf version="1.8">
  <model name="cube_40mm">
    <static>false</static>
    <link name="link">
      <collision name="c"><geometry><box><size>${BLOCK_SIZE} ${BLOCK_SIZE} ${BLOCK_SIZE}</size></box></geometry></collision>
      <visual name="v">
        <geometry><box><size>${BLOCK_SIZE} ${BLOCK_SIZE} ${BLOCK_SIZE}</size></box></geometry>
        <material>
          <ambient>${r} ${g} ${b} 1</ambient>
          <diffuse>${r} ${g} ${b} 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>
EOF
}

CUBE_RED_SDF="${SDF_DIR}/cube_red.sdf";     write_cube_sdf "$CUBE_RED_SDF"     0.85 0.10 0.10
CUBE_BLUE_SDF="${SDF_DIR}/cube_blue.sdf";   write_cube_sdf "$CUBE_BLUE_SDF"    0.10 0.10 0.85
CUBE_YELL_SDF="${SDF_DIR}/cube_yellow.sdf"; write_cube_sdf "$CUBE_YELL_SDF"    0.90 0.85 0.10
# -------------------------------------

# ---------- cleanup old entities ----------
echo "Cleaning up previous lab06 entities (if any)…"
remove_model lab06_table
remove_model lab06_block_red
remove_model lab06_block_blue
remove_model lab06_block_yellow
# -----------------------------------------

# ---------- spawn table ----------
TABLE_CENTER_X="${TABLE_CENTER_X:-0.0}"
TABLE_CENTER_Y="${TABLE_CENTER_Y:-0.0}"
TABLE_CENTER_Z=$(python3 - <<PY
top=${TABLE_TOP_Z}; th=${TABLE_THICK}
print(top - th/2.0)
PY
)
call_create "$TABLE_SDF" "lab06_table" "$TABLE_CENTER_X" "$TABLE_CENTER_Y" "$TABLE_CENTER_Z"
echo "Spawned static table: ${TABLE_SIZE_X}×${TABLE_SIZE_Y}×${TABLE_THICK} m, top @ z=${TABLE_TOP_Z}"

# cube COM so it drops ~BLOCK_DROP onto the table
BLOCK_Z=$(python3 - <<PY
top=${TABLE_TOP_Z}; sz=${BLOCK_SIZE}; drop=${BLOCK_DROP}
print(top + sz/2.0 + drop)
PY
)

# ---------- spawn colored cubes ----------
call_create "$CUBE_RED_SDF"   "lab06_block_red"    "$X"  "-${SPACING}" "$BLOCK_Z"
call_create "$CUBE_BLUE_SDF"  "lab06_block_blue"   "$X"   "0.0"        "$BLOCK_Z"
call_create "$CUBE_YELL_SDF"  "lab06_block_yellow" "$X"   "${SPACING}" "$BLOCK_Z"

echo "Spawned 3 cubes at x=${X}, y=±${SPACING},0, z=${BLOCK_Z}."
echo "Done."
