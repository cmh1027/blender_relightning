DATASET="synthetic"
SCENES=("chair" "ship" "drums" "ficus" "hotdog" "lego" "materials" "mic")
for (( i=0; i<${#SCENES[@]}; i++ )); do
    SCENE=${SCENES[$i]}
    Blender --background gt/${DATASET}/${SCENE}.blend --python relight_gt.py ${DATASET} ${SCENE}
done  
