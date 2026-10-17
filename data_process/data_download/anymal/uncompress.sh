base_path=/mnt/datasets/GNM/raw_data/anymal 
for d in *; do
    curr_path="$base_path/$d"
    for f in $curr_path/*; do
        anymal_state="$curr_path/*anymal_state.bag"
        hdr_state="$curr_path/*hdr_front.bag"
        if [[ $f = $anymal_state ]]; then
            rosbag decompress "$f"
        elif [[ $f = $hdr_state ]]; then
            rosbag decompress "$f"
        fi
    done
done