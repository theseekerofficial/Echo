import os
import random
import logging
from threading import Thread
from modules.configurator import get_env_var_from_db
from PIL import Image, ImageDraw, ImageFont, ImageColor
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

FONT_FILES = ["RoosterPersonalUse-3z8d8.ttf", "Pacifico-Regular.ttf", 
              "RubikMicrobe-Regular.ttf", "Estonia-Regular.ttf", 
              "Sixtyfour-Regular-VariableFont.ttf", "MoiraiOne-Regular.ttf",
              "Stylish-Regular.ttf", "LiquidSky.ttf",
              "Cassandra.ttf", "BlackDestroy.ttf", "Veggy.ttf", "RichTheBarber.ttf", "Scripto.ttf",
              "Organical-Bold-Italic.ttf", "Angelina.ttf", "SingleDay.ttf", "LucySaidOk.ttf"]

GRAPHICS_CATEGORIES = ["Arrows", "Contact", "Elements", "Flags", "Social", "Apple"]

additional_colors = {
    "red": (255, 0, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "pink": (255, 192, 203), "purple": (128, 0, 128), "green": (0, 128, 0),
    "orange": (255, 165, 0), "brown": (165, 42, 42), "black": (0, 0, 0), "gold": (255, 215, 0),
    "white": (255, 255, 255), "gray": (128, 128, 128),"lemon green": (173, 255, 47),
    "dark red": (139, 0, 0), "sky blue": (135, 206, 235),
    "coral": (255, 127, 80), "lavender": (230, 230, 250), "mint green": (152, 255, 152),
    "teal": (0, 128, 128), "maroon": (128, 0, 0), "orchid": (218, 112, 214),
    "salmon": (250, 128, 114), "goldenrod": (218, 165, 32), "periwinkle": (204, 204, 255),
    "olive": (128, 128, 0), "plum": (221, 160, 221), "slate gray": (112, 128, 144),
    "indigo": (75, 0, 130), "turquoise": (64, 224, 208), "tomato": (255, 99, 71),
    "cyan": (0, 255, 255), "chocolate": (210, 105, 30), "lavender blush": (255, 240, 245),
    "midnight blue": (25, 25, 112), "forest green": (34, 139, 34), "papaya whip": (255, 239, 213),
    "dodger blue": (30, 144, 255), "rosy brown": (188, 143, 143), "cadet blue": (95, 158, 160),
    "deep pink": (255, 20, 147), "slate blue": (106, 90, 205), "indian red": (205, 92, 92),
    "dark slate gray": (47, 79, 79), "lemon chiffon": (255, 250, 205), "medium purple": (147, 112, 219),
    "sandy brown": (244, 164, 96), "dark cyan": (0, 139, 139), "lavender blue": (204, 204, 255),
    "light salmon": (255, 160, 122), "cadmium orange": (255, 97, 3), "deep sky blue": (0, 191, 255),
    "rosy violet": (203, 51, 133), "steel blue": (70, 130, 180), "medium aquamarine": (102, 205, 170),
    "paprika": (193, 75, 3), "thistle": (216, 191, 216), "dark olive green": (85, 107, 47),
    "hot pink": (255, 105, 180), "chartreuse": (127, 255, 0), "deep violet": (51, 0, 102),
    "antique white": (250, 235, 215), "spring green": (0, 255, 127), "medium blue": (0, 0, 205),
    "misty rose": (255, 228, 225), "medium orchid": (186, 85, 211), "peru": (205, 133, 63),
    "light slate gray": (119, 136, 153), "pale goldenrod": (238, 232, 170), "firebrick": (178, 34, 34),
    "dark magenta": (139, 0, 139), "lawn green": (124, 252, 0), "deep red": (220, 20, 60),
    "orchid pink": (242, 189, 205), "sienna": (160, 82, 45), "medium slate blue": (123, 104, 238),
    "dark goldenrod": (184, 134, 11), "pale violet red": (219, 112, 147), "lemon yellow": (255, 244, 79),
    "dark sea green": (143, 188, 143), "light coral": (240, 128, 128), "chocolate brown": (210, 105, 30),
    "medium turquoise": (72, 209, 204), "olive drab": (107, 142, 35), "cadmium yellow": (255, 246, 0),
    "light sky blue": (135, 206, 250), "royal blue": (65, 105, 225), "alice blue": (240, 248, 255),
    "antique brass": (205, 149, 117), "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255), "beige": (245, 245, 220), "bisque": (255, 228, 196),
    "blanched almond": (255, 235, 205), "blue violet": (138, 43, 226), "burlywood": (222, 184, 135),
    "cadet grey": (145, 163, 176), "chartreuse green": (127, 255, 0), "coral pink": (248, 131, 121),
    "cornflower blue": (100, 149, 237), "dark blue": (0, 0, 139), "dark brown": (92, 64, 51),
    "dark gray": (169, 169, 169), "dark green": (0, 100, 0), "dark khaki": (189, 183, 107),
    "dark orange": (255, 140, 0), "dark orchid": (153, 50, 204), "dark salmon": (233, 150, 122),
    "dark turquoise": (0, 206, 209), "dark violet": (148, 0, 211), "deep cerulean": (0, 123, 167),
    "dim gray": (105, 105, 105), "dusty rose": (204, 153, 153), "emerald green": (80, 200, 120),
    "fawn": (229, 170, 112), "gainsboro": (220, 220, 220), "ghost white": (248, 248, 255),
    "honeydew": (240, 255, 240), "ivory": (255, 255, 240), "khaki": (240, 230, 140),
    "lavender mist": (230, 230, 250), "light blue": (173, 216, 230), "light cyan": (224, 255, 255),
    "light goldenrod": (250, 250, 210), "light gray": (211, 211, 211), "light green": (144, 238, 144),
    "light pink": (255, 182, 193), "light salmon pink": (255, 153, 153), "light sea green": (32, 178, 170),
    "light sky blue": (135, 206, 250), "light slate blue": (132, 112, 255), "light steel blue": (176, 196, 222),
    "light yellow": (255, 255, 224), "lime green": (50, 205, 50), "linen": (250, 240, 230),
    "magenta": (255, 0, 255), "medium sea green": (60, 179, 113), "medium spring green": (0, 250, 154),
    "mint cream": (245, 255, 250), "navajo white": (255, 222, 173), "navy blue": (0, 0, 128),
    "old lace": (253, 245, 230), "olive green": (128, 128, 0), "orange red": (255, 69, 0),
    "pale blue": (175, 238, 238), "pale green": (152, 251, 152), "pale turquoise": (175, 238, 238),
    "pale violet": (219, 112, 147), "peach puff": (255, 218, 185), "powder blue": (176, 224, 230),
    "pumpkin": (255, 117, 24), "purple": (128, 0, 128), "red violet": (199, 21, 133),
    "rose gold": (183, 110, 121), "royal purple": (120, 81, 169), "saddle brown": (139, 69, 19),
    "saffron": (244, 196, 48), "sea green": (46, 139, 87), "sienna brown": (160, 82, 45),
    "silver": (192, 192, 192), "sky magenta": (207, 113, 175), "snow": (255, 250, 250),
    "tan": (210, 180, 140), "taupe": (72, 60, 50), "vermilion": (227, 66, 52),
    "violet red": (208, 32, 144), "wheat": (245, 222, 179), "white smoke": (245, 245, 245),
    "yellow green": (154, 205, 50)
}

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def parse_description(description):
    description_lower = description.lower()

    text = ""
    text_color = "black"  # Default text color
    bg_color = "white"  # Default background color
    font_size = 175  # Default font size

    # Extract font size if present
    size_parts = description_lower.split(' size ')
    if len(size_parts) > 1 and size_parts[1].isdigit():
        font_size = int(size_parts[1])
        description_lower = size_parts[0]  

    # Extract background color if present
    bg_parts = description_lower.split(' in ')
    if len(bg_parts) > 1:
        description_lower, bg_part = bg_parts
        bg_color = find_color(bg_part.strip(), "white") 

    text, text_color = find_text_and_color(description_lower)

    return text, text_color, bg_color, font_size

def find_text_and_color(description):
    sorted_colors = sorted(additional_colors.keys(), key=len, reverse=True)
    
    for color_name in sorted_colors:
        if color_name in description:
            text_color = rgb_to_hex(additional_colors[color_name])
            text = description.replace(color_name, '').strip().title()
            return text, text_color

    return description.title(), rgb_to_hex(additional_colors["black"])

def find_color(color_text, default_color):
    sorted_colors = sorted(additional_colors.keys(), key=len, reverse=True)
    
    for color_name in sorted_colors:
        if color_name in color_text:
            return rgb_to_hex(additional_colors[color_name])

    return ImageColor.getcolor(color_text, "RGB")
    
def setup_directory(directory="image_gen"):
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")
    else:
        file_count = 0
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    file_count += 1
            except Exception as e:
                logging.error(f"Failed to delete {file_path}. Reason: {e}")

        logging.info(f"Deleted {file_count} file(s) from {directory}")

def add_graphics_to_logo(image, category, pattern, text_area):
    base_directory = os.path.dirname(__file__)
    graphics_dir = os.path.join(base_directory, 'graphics', category)
    graphics_files = [f for f in os.listdir(graphics_dir) if os.path.isfile(os.path.join(graphics_dir, f))]

    if not graphics_files:
        return  # No graphics files in the directory

    placed_graphics = []
    if pattern == 'single':
        num_graphics = 15 
        graphic_file = random.choice(graphics_files)
    elif pattern == 'multi':
        num_graphics = min(16, len(graphics_files))  
        random.shuffle(graphics_files) 

    for i in range(num_graphics):
        if pattern == 'multi':
            graphic_file = graphics_files[i % len(graphics_files)]  
        graphic_path = os.path.join(graphics_dir, graphic_file)
      
        with Image.open(graphic_path) as graphic:
            graphic = graphic.convert("RGBA")
            scale = random.uniform(0.1, 0.3)
            new_size = (int(graphic.width * scale), int(graphic.height * scale))
            graphic = graphic.resize(new_size, Image.Resampling.LANCZOS)

            # Attempt to place the graphic without overlapping the text or other graphics
            for attempt in range(100):  
                x = random.randint(0, image.width - new_size[0])
                y = random.randint(0, image.height - new_size[1])
                proposed_area = (x, y, x + new_size[0], y + new_size[1])

                # Check if the area overlaps with the text area or any other graphic
                if not (overlaps(proposed_area, text_area) or any(overlaps(proposed_area, area) for area in placed_graphics)):
                    break
            else:
                continue  # Skip placing this graphic if no suitable position is found

            angle = random.randint(0, 360)
            graphic = graphic.rotate(angle, expand=1)
            image.paste(graphic, (x, y), graphic)
            placed_graphics.append(proposed_area)

def overlaps(area1, area2):
    return not (area1[2] <= area2[0] or area1[0] >= area2[2] or area1[3] <= area2[1] or area1[1] >= area2[3])

def generate_logo(description, font_name, font_size, graphics_category, graphics_pattern, frame_selection, width=1200, height=800, directory="image_gen"):
    text, text_color, bg_color, _ = parse_description(description)  
    font_file_name = font_name + ".ttf"
    font_path = os.path.join(os.path.dirname(__file__), 'fonts', font_file_name)

    image = Image.new("RGB", (width, height), color=ImageColor.getcolor(bg_color, "RGB"))
    draw = ImageDraw.Draw(image)
  
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        logging.info(f"Failed to load font from {font_path}. Using default font instead.")
        font = ImageFont.load_default()

    text_width = draw.textlength(text, font=font)
    text_height = font_size
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    draw.text((text_x, text_y), text, font=font, fill=ImageColor.getcolor(text_color, "RGB"))

    text_area = (text_x, text_y, text_x + text_width, text_y + text_height)
    if graphics_category and graphics_category != "No Graphics":
        graphics_pattern_resolved = 'single' if graphics_pattern == 'single' else 'multi'
        add_graphics_to_logo(image, graphics_category, graphics_pattern_resolved, text_area)

    if frame_selection != "none":
        frame_index = int(frame_selection) - 1  # Convert to zero-based index
        frame_files = sorted(os.listdir(os.path.join(os.path.dirname(__file__), 'frames')))
        frame_path = os.path.join(os.path.dirname(__file__), 'frames', frame_files[frame_index])
        frame_image = Image.open(frame_path).convert("RGBA")
        frame_image = frame_image.resize(image.size, Image.Resampling.LANCZOS)
        image = Image.alpha_composite(image.convert("RGBA"), frame_image)

    setup_directory(directory)
    image_path = os.path.join(directory, f"logo_{os.getpid()}.png")
    image.save(image_path)
    logging.info(f"Saved image: {image_path}")

    return image_path

def handle_logogen(update: Update, context: CallbackContext):
    # Fetch the LOGOGEN_PLUGIN environment variable from MongoDB
    logogen_plugin_enabled_str = get_env_var_from_db('LOGOGEN_PLUGIN')
    logogen_plugin_enabled = logogen_plugin_enabled_str.lower() == 'true' if logogen_plugin_enabled_str else False

    if logogen_plugin_enabled:
        # Store the user ID of the person who initiated the command
        context.user_data['initiator_user_id'] = update.message.from_user.id
        args = context.args

        # Check if the user provided a description
        if not args:
            # If no description is provided, send an instruction message
            update.message.reply_text(
                "You are using this command incorrectly. Send your logo description "
                "along with /logogen command ✍️. Ex - /logogen red Echo in Black Background"
            )
            return

        description = ' '.join(args)
        context.user_data['logo_description'] = description

        # Split FONT_FILES into chunks for a 3x2 grid
        keyboard = [FONT_FILES[i:i + 3] for i in range(0, len(FONT_FILES), 3)]
        keyboard_buttons = [[InlineKeyboardButton(font.split('.')[0], callback_data="logo_font_" + font.split('.')[0]) for font in row] for row in keyboard]
        keyboard_buttons.append([InlineKeyboardButton("Random Font", callback_data="logo_font_random")])

        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        update.message.reply_text("Select a Font for logo Generate", reply_markup=reply_markup)

    else:
        # If LOGOGEN_PLUGIN is False, anything else, or not set
        update.message.reply_text(
            "Logo Gen Plugin Disabled by the person who deployed this Echo Variant 💔"
        )

# New function to handle graphics selection
def handle_graphics_selection(update: Update, context: CallbackContext):
    keyboard = [["Arrows", "Contact", "Elements"], ["Flags", "Social", "Apple"], ["Random Graphics", "No Graphics"]]
    keyboard_buttons = [[InlineKeyboardButton(text, callback_data="logo_gra_" + text.replace(" ", "_")) for text in row] for row in keyboard]
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    update.message.reply_text("Now choose a Graphics category", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    initiator_user_id = context.user_data.get('initiator_user_id')

    # Check if the user interacting is the same as the one who initiated /logogen
    if query.from_user.id != initiator_user_id:
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /logogen if you want to gen a logo", show_alert=True)
        return  # Stop processing this callback

    data = query.data
  
    # Check if the selection is for a font
    if data.startswith("logo_font_"):
        if data == "logo_font_random":
            # Choose a random font from FONT_FILES
            font_name = random.choice(FONT_FILES).split('.')[0]
        else:
            font_name = data.split("_")[2]
        
        context.user_data['selected_font'] = font_name

        # Show graphics category selection by updating the existing message
        keyboard = [
            ["Arrows", "Contact", "Elements"], 
            ["Flags", "Social", "Apple"], 
            ["Random Graphics", "No Graphics"]
        ]
        keyboard_buttons = [
            [InlineKeyboardButton(text, callback_data="logo_gra_" + text.replace(" ", "_")) for text in row]
            for row in keyboard
        ]
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        query.edit_message_text(text="Now choose a Graphics category", reply_markup=reply_markup)

    # Handle graphics category selection
    elif data.startswith("logo_gra_"):
        if data == "logo_gra_Random_Graphics":
            # Choose a random graphics category
            graphics_category = random.choice(GRAPHICS_CATEGORIES)
        else:
            graphics_category = data.split("_", 2)[2].replace("_", " ")
    
        context.user_data['graphics_category'] = graphics_category

        if graphics_category == "No Graphics":
            # Skip to font size selection if "No Graphics" is selected
            font_sizes = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 500]
            keyboard = [font_sizes[i:i + 3] for i in range(0, len(font_sizes), 3)]  # Split the sizes into rows for a 3x4 grid
            keyboard_buttons = [[InlineKeyboardButton(str(size), callback_data=f"font_size_{size}") for size in row] for row in keyboard]
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            query.edit_message_text(text="Now choose a Font Size", reply_markup=reply_markup)
        else:
            # Show graphics pattern selection for other categories
            keyboard = [
                [InlineKeyboardButton("Single-Graphic Repeating", callback_data="logo_pattern_single")],
                [InlineKeyboardButton("Multi-Graphics Repeating", callback_data="logo_pattern_multi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="Now choose a Graphics pattern", reply_markup=reply_markup)

    # Handle graphics pattern selection
    elif data.startswith("logo_pattern_"):
        graphics_pattern = 'single' if data.endswith("single") else 'multi'
        context.user_data['graphics_pattern'] = graphics_pattern
    
        # Show font size selection by updating the existing message
        font_sizes = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 500]
        keyboard = [font_sizes[i:i + 3] for i in range(0, len(font_sizes), 3)]  # Split the sizes into rows for a 3x4 grid
        keyboard_buttons = [[InlineKeyboardButton(str(size), callback_data=f"font_size_{size}") for size in row] for row in keyboard]
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        query.edit_message_text(text="Now choose a Font Size", reply_markup=reply_markup)

    # Handle font size selection
    elif data.startswith("font_size_"):
        font_size = int(data.split("_")[2])
        context.user_data['font_size'] = font_size
    
        # Show frame selection by updating the existing message
        frames_dir = os.path.join(os.path.dirname(__file__), 'frames')
        frame_files = [f for f in os.listdir(frames_dir) if os.path.isfile(os.path.join(frames_dir, f))]
        frame_buttons = [InlineKeyboardButton(f"Frame {i+1}", callback_data=f"frame_{i+1}") for i in range(len(frame_files))]
        frame_buttons.append(InlineKeyboardButton("No Frame", callback_data="frame_none"))
    
        # Arrange the buttons in a 6x3 layout with the "No Frame" button
        keyboard = [frame_buttons[i:i + 3] for i in range(0, len(frame_buttons), 3)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="Now choose a frame for your logo", reply_markup=reply_markup)

    # Handle frame selection
    elif data.startswith("frame_"):
        frame_selection = data.split("_")[1]
        context.user_data['frame_selection'] = frame_selection
        # Delete the frame selection message
        query.message.delete()
        proceed_to_logo_creation(update, context)

def proceed_to_logo_creation(update, context):
    font_name = context.user_data.get('selected_font', 'default_font')
    font_size = context.user_data.get('font_size', 150)  # Default size if not selected, though now you always expect a selection
    description = context.user_data.get('logo_description', "")
    graphics_category = context.user_data.get('graphics_category', None)
    graphics_pattern = context.user_data.get('graphics_pattern', None)
    frame_selection = context.user_data.get('frame_selection', None)

    # Start a separate thread to create and send the logo
    thread = Thread(target=create_and_send_logo, args=(update, context, description, font_name, font_size, graphics_category, graphics_pattern, frame_selection))
    thread.start()
  
def create_and_send_logo(update, context, description, font_name, font_size, graphics_category, graphics_pattern, frame_selection):
    try:
        # Generate the logo
        logo_image_path = generate_logo(description, font_name, font_size, graphics_category, graphics_pattern, frame_selection)

        # Send the logo
        with open(logo_image_path, 'rb') as file:
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=file)

        # Delete the logo file
        delete_image(logo_image_path)

        # Logging
        username = update.effective_user.username
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        logging.info(f"User @{username} (ID: {user_id}) generated a logo in chat ID: {chat_id}.🎨🖌️ | "
                     f"Description: {description}, Graphics: {graphics_category}, Graphic Pattern: {graphics_pattern}, Font: {font_name}, Font Size: {font_size}, Frame: {frame_selection}⚙️")

    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}")
        logging.error(f"Failed to generate logo for user @{update.effective_user.username} (ID: {update.effective_user.id}): {e}")

def delete_image(image_path):
    try:
        os.remove(image_path)
        logging.info(f"Deleted image: {image_path}")
    except Exception as e:
        logging.error(f"Failed to delete {image_path}. Reason: {e}")
