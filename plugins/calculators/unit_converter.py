# unit_converter.py in plugins/calculators/
import logging
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Units and their conversion factors to meters
LENGTH_UNITS = {
    "Meter": 1,
    "Centimeter": 0.01,
    "Millimeter": 0.001,
    "Kilometer": 1000,
    "Inch": 0.0254,
    "Foot": 0.3048,
    "Yard": 0.9144,
    "Mile": 1609.34
}

# Units and their conversion factors to square meters
AREA_UNITS = {
    "Square Meter": 1,
    "Square Kilometer": 1e6,
    "Square Centimeter": 1e-4,
    "Square Inch": 0.00064516,
    "Square Foot": 0.092903,
    "Square Yard": 0.836127,
    "Acre": 4046.86,
    "Hectare": 10000
}

# Units and their conversion factors to liters
VOLUME_UNITS = {
    "Liter": 1,
    "Milliliter": 0.001,
    "Cubic Meter": 1000,
    "Cubic Centimeter": 0.001,
    "Cubic Inch": 0.0163871,
    "Cubic Foot": 28.3168,
    "Gallon": 3.78541,
    "Uk Gallon": 4.54609,
    "Fluid Ounce": 0.0295735,
    "Uk Fluid Ounce": 0.0284131
}

# Units and their conversion factors to kilograms
WEIGHT_UNITS = {
    "Kilogram": 1,
    "Gram": 0.001,
    "Milligram": 1e-6,
    "Pound": 0.453592,
    "Ounce": 0.0283495,
    "Stone": 6.35029,
    "Metric Ton": 1000
}

# Units and their conversion factors to seconds
TIME_UNITS = {
    "Second": 1,
    "Minute": 60,
    "Hour": 3600,
    "Day": 86400,
    "Week": 604800,
    "Month": 2629800,  
    "Year": 31557600   
}

SPEED_UNITS = {
    "Meters Per Second": 1,
    "Kilometers Per Hour": 0.277778,  
    "Miles Per Hour": 0.44704,      
    "Feet Per Second": 0.3048,    
    "Knots": 0.514444,              
    "Mach": 343              
}

PRESSURE_UNITS = {
    "Pascal": 1,
    "Kilopascal": 1000,
    "Megapascal": 1000000,
    "Bar": 100000,
    "Millimeter Of Mercury": 133.322,
    "Atmosphere": 101325
}

ENERGY_UNITS = {
    "Joule": 1,
    "Kilojoule": 1000,
    "Calorie": 4.184,
    "Kilocalorie": 4184,
    "Watt Hour": 3600,
    "Kilowatt Hour": 3.6e6
}

POWER_UNITS = {
    "Watt": 1,
    "Kilowatt": 1000,
    "Megawatt": 1000000,
    "Horsepower": 745.7
}
ANGLE_UNITS = {
    "Degree": 1,
    "Radian": 57.2958,
    "Gradian": 0.9
}

DIGITAL_STORAGE_UNITS = {
    "Bit": 1,
    "Byte": 8,
    "Kilobyte": 1024 * 8,
    "Megabyte": 1024 * 1024 * 8,
    "Gigabyte": 1024 * 1024 * 1024 * 8,
    "Terabyte": 1024 * 1024 * 1024 * 1024 * 8,
    "Petabyte": 1024 * 1024 * 1024 * 1024 * 1024 * 8,
    "Exabyte": 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 8,
    "Zettabyte": 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 8,
    "Yottabyte": 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 8,
    "Brontobyte": 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 8
}

FUEL_EFFICIENCY_UNITS = {
    "Miles Per Gallon": 1,
    "Kilometers Per Liter": 2.35214583
}

COOKING_UNITS = {
    "Teaspoon": 1,
    "Tablespoon": 3,
    "Cup": 48,            
    "Fluid Ounce": 6,     
    "Milliliter": 0.202884,  
    "Gram": 0.00591939,      
    "Pound": 96             
}

TEMPERATURE_UNITS = {
    "Celsius": 1,  
    "Fahrenheit": 2,  
    "Kelvin": 3  
}

# State of the unit conversion for each user
unit_converter_state = {}

def start_unit_converter(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Logging the start of unit converter session
    logger.info(f"User {user_id} started unit converter in chat {chat_id} ⚖️📏🔄")

    # Initialize state for the user
    unit_converter_state[(chat_id, message_id)] = {
        "user_id": user_id,  
        "category": None,    
        "first_unit": None,  
        "second_unit": None, 
        "value": ""          
    }

    # Display category selection
    keyboard = [
    [InlineKeyboardButton("Length", callback_data="length"), InlineKeyboardButton("Volume", callback_data="volume"), InlineKeyboardButton("Area", callback_data="area")],
    [InlineKeyboardButton("Weight/Mass", callback_data="weight"), InlineKeyboardButton("Time", callback_data="time"), InlineKeyboardButton("Speed", callback_data="speed")],
    [InlineKeyboardButton("Pressure", callback_data="pressure"), InlineKeyboardButton("Energy", callback_data="energy"), InlineKeyboardButton("Power", callback_data="power")],
    [InlineKeyboardButton("Angle", callback_data="angle"), InlineKeyboardButton("Data Spectrum", callback_data="digital_storage"), InlineKeyboardButton("Fuel Efficiency", callback_data="fuel_efficiency")],
    [InlineKeyboardButton("Cooking", callback_data="cooking"), InlineKeyboardButton("Temperature", callback_data="temperature")],
    [InlineKeyboardButton("Unit Converter Instructions (Read Before Use)", callback_data="unit_converter_instruction")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("Choose a Category", reply_markup=reply_markup)

def show_unit_converter_instructions(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    instructions = """
<b>Here is how to use Unit Converter:</b>

1. <i>Start</i> the conversion by selecting a category (e.g., Length, Volume).
2. Choose the <b>first unit</b> from the provided list.
3. Choose the <b>second unit</b> for conversion.
4. <i>Enter</i> the numeric value for conversion using the numeric keyboard.
5. Press '<code>Enter</code>' to perform the conversion.
6. View the <b>result</b> and there are options for making another calculation or closing the conversion for your easy.

<b><u>Special Unit Instructions;</u></b>
◘ <code>In Data Spectrum category unit converter using 1024 = 1 value format. Not using 1000 = 1 value format</code>

Enjoy using the Echo's Unit Converter! 📏🔄
    """
    context.bot.send_message(chat_id=user_id, text=instructions, parse_mode=ParseMode.HTML)

def select_length_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific unit converter instance
    converter_state = unit_converter_state.get((chat_id, message_id), {})

    # Generate unit selection buttons in a 4x2 grid
    units = list(LENGTH_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"l_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Length | {stage}", reply_markup=reply_markup)

def select_area_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    # Similar implementation as select_length_unit but use AREA_UNITS
    units = list(AREA_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"a_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Area | {stage}", reply_markup=reply_markup)

def select_volume_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(VOLUME_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"v_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Volume | {stage}", reply_markup=reply_markup)

def select_weight_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(WEIGHT_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"w_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Weight/Mass | {stage}", reply_markup=reply_markup)

def select_time_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(TIME_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"ti_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Time | {stage}", reply_markup=reply_markup)

def select_speed_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(SPEED_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"sp_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Speed | {stage}", reply_markup=reply_markup)

def select_pressure_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(PRESSURE_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"p_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Pressure | {stage}", reply_markup=reply_markup)

def select_energy_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(ENERGY_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"en_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Energy | {stage}", reply_markup=reply_markup)

def select_power_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(POWER_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"pw_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Power | {stage}", reply_markup=reply_markup)

def select_angle_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(ANGLE_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"an_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Angle | {stage}", reply_markup=reply_markup)

def select_digital_storage_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(DIGITAL_STORAGE_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"ds_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Digital Storage | {stage}", reply_markup=reply_markup)

def select_fuel_efficiency_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(FUEL_EFFICIENCY_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"fe_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Fuel Efficiency | {stage}", reply_markup=reply_markup)

def select_cooking_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(COOKING_UNITS.keys())
    keyboard = []
    for i in range(0, len(units), 2):
        row = []
        for unit in units[i:i+2]:
            callback_data = f"ck_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
            row.append(InlineKeyboardButton(unit, callback_data=callback_data))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Cooking | {stage}", reply_markup=reply_markup)

def convert_temperature(value, from_unit, to_unit):
    if from_unit == "Celsius":
        if to_unit == "Fahrenheit":
            return (value * 9/5) + 32
        elif to_unit == "Kelvin":
            return value + 273.15
    elif from_unit == "Fahrenheit":
        if to_unit == "Celsius":
            return (value - 32) * 5/9
        elif to_unit == "Kelvin":
            return (value - 32) * 5/9 + 273.15
    elif from_unit == "Kelvin":
        if to_unit == "Celsius":
            return value - 273.15
        elif to_unit == "Fahrenheit":
            return (value - 273.15) * 9/5 + 32
    return value  # If from_unit and to_unit are the same

def select_temperature_unit(update: Update, context: CallbackContext, is_first_unit=True):
    query = update.callback_query
    units = list(TEMPERATURE_UNITS.keys())
    keyboard = []
    for unit in units:
        callback_data = f"tem_{'first' if is_first_unit else 'second'}_{unit.lower().replace(' ', '_')}"
        keyboard.append([InlineKeyboardButton(unit, callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("Back", callback_data="unit_cat_to_cho_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    stage = "1st Unit Input" if is_first_unit else "2nd Unit Input"
    query.edit_message_text(f"Category: Temperature | {stage}", reply_markup=reply_markup)

def handle_back_to_category(update: Update, context: CallbackContext):
    query = update.callback_query

    # Display 'Choose a Category' message with buttons
    keyboard = [
    [InlineKeyboardButton("Length", callback_data="length"), InlineKeyboardButton("Volume", callback_data="volume"), InlineKeyboardButton("Area", callback_data="area")],
    [InlineKeyboardButton("Weight/Mass", callback_data="weight"), InlineKeyboardButton("Time", callback_data="time"), InlineKeyboardButton("Speed", callback_data="speed")],
    [InlineKeyboardButton("Pressure", callback_data="pressure"), InlineKeyboardButton("Energy", callback_data="energy"), InlineKeyboardButton("Power", callback_data="power")],
    [InlineKeyboardButton("Angle", callback_data="angle"), InlineKeyboardButton("Data Spectrum", callback_data="digital_storage"), InlineKeyboardButton("Fuel Efficiency", callback_data="fuel_efficiency")],
    [InlineKeyboardButton("Cooking", callback_data="cooking"), InlineKeyboardButton("Temperature", callback_data="temperature")],
    [InlineKeyboardButton("Unit Converter Instructions (Read Before Use)", callback_data="unit_converter_instruction")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("Choose a Category", reply_markup=reply_markup)

def handle_unit_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific unit converter instance
    converter_state = unit_converter_state.get((chat_id, message_id), {})

    if user_id != converter_state.get("user_id"):
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use the unit converter", show_alert=True)
        return  # Exit the function

    data = query.data.split("_")
    category_prefix = data[0]

    if category_prefix in ["tem", "ck", "fe", "ds", "an", "pw", "en", "p", "sp", "ti", "w", "v", "a", "l"]:  # Prefix for Weight, Volume, Area, Length
        category = {"tem": "temperature", "ck": "cooking", "fe": "fuel_efficiency", "ds": "digital_storage", "an": "angle", "pw": "power", "en": "energy", "p": "pressure", "sp": "speed", "ti": "time", "w": "weight", "v": "volume", "a": "area", "l" : "length"}.get(category_prefix, "length")
        unit_type = data[1]
        unit_name = "_".join(data[2:]) 

        converter_state["category"] = category
        converter_state[unit_type + "_unit"] = unit_name

        if unit_type == "first":
            if category == "temperature":
                select_temperature_unit(update, context, is_first_unit=False)
            elif category == "cooking":
                select_cooking_unit(update, context, is_first_unit=False)
            elif category == "fuel_efficiency":
                select_fuel_efficiency_unit(update, context, is_first_unit=False)
            elif category == "digital_storage":
                select_digital_storage_unit(update, context, is_first_unit=False)
            elif category == "angle":
                select_angle_unit(update, context, is_first_unit=False)
            elif category == "power":
                select_power_unit(update, context, is_first_unit=False)
            elif category == "energy":
                select_energy_unit(update, context, is_first_unit=False)
            elif category == "pressure":
                select_pressure_unit(update, context, is_first_unit=False)
            elif category == "speed":
                select_speed_unit(update, context, is_first_unit=False)
            elif category == "time":
                select_time_unit(update, context, is_first_unit=False)
            elif category == "weight":
                select_weight_unit(update, context, is_first_unit=False)
            elif category == "volume":
                select_volume_unit(update, context, is_first_unit=False)
            elif category == "area":
                select_area_unit(update, context, is_first_unit=False)
            else:  # Length
                select_length_unit(update, context, is_first_unit=False)
        elif unit_type == "second":
            show_numeric_keyboard(update, context)

    # Update the session state
    unit_converter_state[(chat_id, message_id)] = converter_state

def show_numeric_keyboard(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific unit converter instance
    converter_state = unit_converter_state.get((chat_id, message_id), {})

    if user_id != converter_state.get("user_id"):
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use the unit converter", show_alert=True)
        return  # Exit the function

    # Generate and show the numeric keyboard
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"unit_cal_{i}") for i in range(1, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"unit_cal_{i}") for i in range(4, 7)],
        [InlineKeyboardButton(str(i), callback_data=f"unit_cal_{i}") for i in range(7, 10)],
        [InlineKeyboardButton("AC", callback_data="unit_cal_ac"), InlineKeyboardButton("0", callback_data="unit_cal_0"), InlineKeyboardButton(".", callback_data="unit_cal_dot")],
        [InlineKeyboardButton("Backspace", callback_data="unit_cal_backspace"), InlineKeyboardButton("Enter", callback_data="unit_cal_enter")]
    ]
    # Add 'Back' button to the numeric keyboard
    keyboard.append([InlineKeyboardButton("Back", callback_data="num_pad_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("Enter Value:", reply_markup=reply_markup)

def handle_num_pad_back(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Logic to go back to "Category: Length | 2nd Unit Input"
    select_length_unit(update, context, is_first_unit=False)

def handle_numeric_input(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific unit converter instance
    converter_state = unit_converter_state.get((chat_id, message_id), {})

    if user_id != converter_state.get("user_id"):
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use the unit converter", show_alert=True)
        return  # Exit the function

    data = query.data

    # Handle numeric input, backspace, enter, AC (All Clear), and "." (Decimal) button presses
    if data == "unit_cal_backspace":
        converter_state["value"] = converter_state["value"][:-1]
    elif data == "unit_cal_enter":
        perform_conversion(update, context)
        return
    elif data == "unit_cal_ac":
        converter_state["value"] = ""  # Clear the value
    elif data == "unit_cal_dot":
        # Add a decimal point if it's not already present
        if "." not in converter_state["value"]:
            converter_state["value"] += "."
    else:
        # Extract the numeric value from callback data and append it
        numeric_value = data.split("_")[2]
        converter_state["value"] += numeric_value

    # Update the session state
    unit_converter_state[(chat_id, message_id)] = converter_state

    # Update the message text with the current value
    query.edit_message_text(f"Entered Value: {converter_state['value']}", reply_markup=query.message.reply_markup)
    query.answer()

def perform_conversion(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific unit converter instance
    converter_state = unit_converter_state.get((chat_id, message_id), {})

    if user_id != converter_state.get("user_id"):
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use the unit converter", show_alert=True)
        return  # Exit the function

    try:
        value = float(converter_state["value"])
        category = converter_state["category"]

        if category == "temperature":
            # Use the convert_temperature function for temperature conversions
            from_unit = converter_state["first_unit"].replace('_', ' ').title()
            to_unit = converter_state["second_unit"].replace('_', ' ').title()
            converted_value = convert_temperature(value, from_unit, to_unit)
            result_message = f"{value} {from_unit} = {converted_value} {to_unit}"
        else:
            # For other categories, use the respective conversion factors
            first_unit_factor = globals()[category.upper() + "_UNITS"][converter_state["first_unit"].replace('_', ' ').title()]
            second_unit_factor = globals()[category.upper() + "_UNITS"][converter_state["second_unit"].replace('_', ' ').title()]
            converted_value = value * first_unit_factor / second_unit_factor
            result_message = f"{value} {converter_state['first_unit'].replace('_', ' ').title()} = {converted_value} {converter_state['second_unit'].replace('_', ' ').title()}"

        # Logging the conversion result
        logger.info(f"User {user_id} converted {value} {converter_state['first_unit']} to {converted_value} {converter_state['second_unit']} in chat {chat_id}")

    except Exception as e:
        logger.error(f"Error in conversion: {e}")
        result_message = "Error in conversion. Please check your input."

    # Add additional buttons to the result message
    keyboard = [
        [InlineKeyboardButton("Make Another Calculation", callback_data="make_another_calc")],
        [InlineKeyboardButton("Close", callback_data="close_conversion")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(result_message, reply_markup=reply_markup)

def handle_make_another_calc(update: Update, context: CallbackContext):
    query = update.callback_query
    start_unit_converter(update, context)

def handle_close_conversion(update: Update, context: CallbackContext):
    query = update.callback_query
    query.message.delete()

def setup_unit_converter(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(start_unit_converter, pattern='^unit_converter$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_back_to_category, pattern='^unit_cat_to_cho_back$'))
    
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^l_(first|second)_.*$'))  
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^a_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^v_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^w_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^ti_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^sp_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^p_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^en_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^pw_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^an_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^ds_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^fe_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^ck_(first|second)_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_unit_selection, pattern='^tem_(first|second)_.*$'))


    dispatcher.add_handler(CallbackQueryHandler(handle_numeric_input, pattern='^unit_cal_(\d|backspace|enter)$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_numeric_input, pattern='^unit_cal_ac$'))  
    dispatcher.add_handler(CallbackQueryHandler(handle_numeric_input, pattern='^unit_cal_dot$'))  

    dispatcher.add_handler(CallbackQueryHandler(select_volume_unit, pattern='^volume$'))
    dispatcher.add_handler(CallbackQueryHandler(select_length_unit, pattern='^length$'))
    dispatcher.add_handler(CallbackQueryHandler(select_area_unit, pattern='^area$'))
    dispatcher.add_handler(CallbackQueryHandler(select_weight_unit, pattern='^weight$'))
    dispatcher.add_handler(CallbackQueryHandler(select_time_unit, pattern='^time$'))
    dispatcher.add_handler(CallbackQueryHandler(select_speed_unit, pattern='^speed$'))
    dispatcher.add_handler(CallbackQueryHandler(select_pressure_unit, pattern='^pressure$'))
    dispatcher.add_handler(CallbackQueryHandler(select_energy_unit, pattern='^energy$'))
    dispatcher.add_handler(CallbackQueryHandler(select_power_unit, pattern='^power$'))
    dispatcher.add_handler(CallbackQueryHandler(select_angle_unit, pattern='^angle$'))
    dispatcher.add_handler(CallbackQueryHandler(select_digital_storage_unit, pattern='^digital_storage$'))
    dispatcher.add_handler(CallbackQueryHandler(select_fuel_efficiency_unit, pattern='^fuel_efficiency$'))
    dispatcher.add_handler(CallbackQueryHandler(select_cooking_unit, pattern='^cooking$'))
    dispatcher.add_handler(CallbackQueryHandler(select_temperature_unit, pattern='^temperature$'))
    
    dispatcher.add_handler(CallbackQueryHandler(handle_num_pad_back, pattern='^num_pad_back$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_make_another_calc, pattern='^make_another_calc$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_close_conversion, pattern='^close_conversion$'))
    dispatcher.add_handler(CallbackQueryHandler(show_unit_converter_instructions, pattern='^unit_converter_instruction$'))
