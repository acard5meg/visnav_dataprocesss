import argparse
import matplotlib as plt
from PIL import Image, ImageOps
import os

width, height = 400, 400

max_size = (width, width)
def construct_image(args: argparse.Namespace):
    '''
    This image will be 3x5
    '''

    full_image = Image.new("RGBA", (width*5, height*3))
    
    row, col = 0,0

    for i in sorted(os.listdir(args.input_filepath)):
        raw_img = Image.open(os.path.join(args.input_filepath, i))
        raw_img = ImageOps.cover(raw_img, max_size)
        full_image.paste(raw_img, (width*row, height*col))

        row+=1

        if row == 5:
            col += 1
            row = 0

    full_image.save('figures/cover_image.png')





if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_filepath",
        type=str,
        help="where data located",
        required=True,
    )
    


    args = parser.parse_args()

    construct_image(args)