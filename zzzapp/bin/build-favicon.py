#!/opt/zzz/venv/bin/python3

#-----favicon image generator with custom text-----
from PIL import Image, ImageDraw, ImageFont

import argparse
import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#--------------------------------------------------------------------------------

output_dir = '/var/www/html/img/custom/'

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

print('build-favicon START\n', flush=True)

if ConfigData['Favicon']['error']:
    sys.exit(ConfigData['Favicon']['error'])

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Zzz script to build custom favicons')
arg_parser.add_argument('-t', '--test', dest='test', action='store_true', help='Test the favicon config without generating files')
args = arg_parser.parse_args()

#-----just report the favicon-related config tests and exit-----
# error is printed above in sys.exit
if args.test:
    print('favicon configtest OK')
    sys.exit()

if not ConfigData['Favicon']['use_custom']:
    sys.exit('Favicon use_custom is False, exiting')

#--------------------------------------------------------------------------------

def find_max_width(image_font, text_lines):
    max_width = 0
    for line in text_lines:
        if not line:
            continue
        width = image_font.getlength(text=line)
        if width>max_width:
            max_width = width
    return max_width

#-----make the text almost fill the box, without going outside the border-----
# acceptable widths: 440-480 (about 85-95% of 512px image width)
# font size should be a multiple of 8 to avoid crashing the font renderer
def auto_adjust_font(ttf_file, text_lines):
    # start with a reasonably large font
    font_size = 224
    # with 1 line, fonts larger than 480 will go outside the vertical space
    max_font_size = 480
    if len(text_lines)==2:
        # with 2 lines, fonts larger than 280 will go outside the vertical space
        max_font_size = 280
    if len(text_lines)==3:
        # start with a font somewhat smaller than the max
        font_size = 152
        # with 3 lines, fonts larger than 184 will go outside the vertical space
        max_font_size = 184
    image_font = ImageFont.truetype(font=ttf_file, size=font_size)
    max_width = find_max_width(image_font, text_lines)

    if max_width>480:
        # text too wide? reduce it until the width is OK
        while max_width>480:
            font_size -= 8
            image_font = ImageFont.truetype(font=ttf_file, size=font_size)
            max_width = find_max_width(image_font, text_lines)
    elif max_width<440:
        # text too narrow? increase it until the width is OK
        while max_width<440 and font_size<max_font_size:
            font_size += 8
            image_font = ImageFont.truetype(font=ttf_file, size=font_size)
            max_width = find_max_width(image_font, text_lines)
    
    return max_width, font_size, image_font

#--------------------------------------------------------------------------------

def make_largest_image(ConfigData, output_dir, text_lines):
    image = Image.new(mode="RGB", size=(512, 512), color="black")
    image_draw = ImageDraw.Draw(image)

    # red, green, blue, opacity
    fill_params = (0, 255 , 0 , 255)

    # middle of the image
    coord_center = (256, 256)

    #-----load a font-----
    # image_font = ImageFont.load_default()
    ttf_file = '/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Regular.ttf'

    max_width, font_size, image_font = auto_adjust_font(ttf_file, text_lines)
    text_combined = '\n'.join(text_lines)

    #-----render the image-----
    image_draw.multiline_text(xy=coord_center, text=text_combined, font=image_font, fill=fill_params, align='center', anchor='mm')

    #-----save the image to a file-----
    image.save(fp=f'{output_dir}/favicon-512.png', format='PNG')

    return image

#--------------------------------------------------------------------------------

def make_smaller_images(ConfigData, image):
    # android sizes:
    # 196x196

    # apple-touch-icon sizes:
    # 120x120
    # 152x152
    # 167x167
    # 180x180

    # browser sizes: 16, 32, 57, 76, 96, 128, 192, 228
    # also 48px to let chrome display it as 32px on a high-density screen

    image_sizes = ConfigData['Favicon']['sizes']['android']
    image_sizes.extend(ConfigData['Favicon']['sizes']['apple'])
    image_sizes.extend(ConfigData['Favicon']['sizes']['browser'])
    image_sizes.extend(ConfigData['Favicon']['sizes']['high_density'])
    for image_size in image_sizes:
        print(f'generating {image_size}x{image_size}')
        filepath = f'{output_dir}/favicon-{image_size}.png'
        image.resize((image_size, image_size)).save(filepath, format='PNG')

#--------------------------------------------------------------------------------

# zzz.conf entries:
#   Favicon:
#       use_custom: 'False'
#       line1: 'ZZZ'
#       line2: 'VPN'
#       line3: ''
# custom images end up in a custom directory:
#   https://services.zzz.zzz/img/custom/favicon-512.png

# fetch custom text from ConfigData
text_line1 = ConfigData['Favicon']['line1']
text_line2 = ConfigData['Favicon']['line2']
text_line3 = ConfigData['Favicon']['line3']
print(f'using custom text:\n{text_line1}\n{text_line2}\n{text_line3}\n')

text_lines = [text_line1]
if text_line2:
    text_lines.append(text_line2)
    # don't add line3 if there is no line2
    if text_line3:
        text_lines.append(text_line3)

image = None
try:
    image = make_largest_image(ConfigData, output_dir, text_lines)
except:
    sys.exit('ERROR: failed to make largest image')

try:
    make_smaller_images(ConfigData, image)
except:
    sys.exit('ERROR: failed to make smaller images')

#TODO: copy from temp dir to production


print('\nbuild-favicon DONE')
