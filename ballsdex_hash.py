import json
from PIL import Image
import imagehash
import os

BALLSDEX_IMAGE_PATH = 'ballsdex'
JSON_PATH = 'ballsdex_hashes.json'


def hash_balldex_images():
    hashes = {}
    images = os.listdir(BALLSDEX_IMAGE_PATH)
    for image_path in images:
        if image_path.endswith('.png'):
            image_hash = str(imagehash.dhash(Image.open(BALLSDEX_IMAGE_PATH + '/' + image_path)))
            hashes[image_hash] = image_path[:-4]
    json_file = open(JSON_PATH, 'w')
    json.dump(hashes, json_file)
    json_file.close()
    return


def check_balldex_image(image_path):
    original_hash = str(imagehash.dhash(Image.open(image_path)))
    json_file = open(JSON_PATH, 'r')
    hash_dict = json.load(json_file)
    json_file.close()
    return hash_dict.get(original_hash)