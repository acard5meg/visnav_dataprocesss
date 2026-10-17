import argparse
import os


def count_pairs(input_dir):
    '''
    input_dir must be the high level directory
    '''
    total_pairs = 0

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            # if decompress bag don't want to process compressed version
            if file.endswith(".jpg"):
                total_pairs += 1
    return total_pairs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--input_filepath",
        required=True,
        type=str
    )

    args = parser.parse_args()

    print(f"The total numer of pairs is: {count_pairs(args.input_filepath)}")
