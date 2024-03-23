# plugins/calculator/calculator.py

import os
import re
import logging
from asteval import Interpreter
from modules.token_system import TokenSystem
from modules.configurator import get_env_var_from_db
from plugins.calculators.unit_converter import setup_unit_converter  
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from plugins.calculators.sci_calculator import show_scientific_calculator
from telegram.ext import CallbackQueryHandler, CallbackContext, CommandHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

token_system = TokenSystem(os.getenv("MONGODB_URI"), "Echo", "user_tokens")

calculator_state = {}

aeval = Interpreter()

def get_keyboard(expression=""):
    keyboard = [
        [InlineKeyboardButton("AC", callback_data="AC"), InlineKeyboardButton("+/-", callback_data="+/-"), InlineKeyboardButton("%", callback_data="%"), InlineKeyboardButton("⌫", callback_data="backspace"), InlineKeyboardButton("÷", callback_data="/")],
        [InlineKeyboardButton("7", callback_data="7"), InlineKeyboardButton("8", callback_data="8"), InlineKeyboardButton("9", callback_data="9"), InlineKeyboardButton("×", callback_data="*")],
        [InlineKeyboardButton("4", callback_data="4"), InlineKeyboardButton("5", callback_data="5"), InlineKeyboardButton("6", callback_data="6"), InlineKeyboardButton("-", callback_data="-")],
        [InlineKeyboardButton("1", callback_data="1"), InlineKeyboardButton("2", callback_data="2"), InlineKeyboardButton("3", callback_data="3"), InlineKeyboardButton("+", callback_data="+")],
        [InlineKeyboardButton("0", callback_data="0"), InlineKeyboardButton(".", callback_data="."), InlineKeyboardButton("=", callback_data="=")]
    ]
    additional_buttons = [
        InlineKeyboardButton("Close", callback_data="basic_cal_close"),
        InlineKeyboardButton("Back", callback_data="basic_cal_back")
    ]
    keyboard.append(additional_buttons)  
    return InlineKeyboardMarkup(keyboard)

def start_calculator(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {username} ({user_id}) opened the Calculator Menu 📃")

    # Check environment variables for each calculator type
    basic_cal_enabled = get_env_var_from_db('CALCULATOR_PLUGIN') == 'True'
    sci_cal_enabled = get_env_var_from_db('SCI_CALCULATOR_PLUGIN') == 'True'
    unit_converter_enabled = get_env_var_from_db('UNIT_CONVERTER_PLUGIN') == 'True'

    # Create buttons based on the environment variable settings
    keyboard = []

    # Basic Calculator Button
    if basic_cal_enabled:
        keyboard.append([InlineKeyboardButton("Basic Calculator", callback_data="show_calculator")])
    else:
        keyboard.append([InlineKeyboardButton("Basic Calculator", callback_data="disabled_calculator")])

    # Scientific Calculator Button
    if sci_cal_enabled:
        keyboard.append([InlineKeyboardButton("Scientific Calculator", callback_data="show_scientific_calculator")])
    else:
        keyboard.append([InlineKeyboardButton("Scientific Calculator", callback_data="disabled_sci_calculator")])

    # Unit Converter Button
    if unit_converter_enabled:
        keyboard.append([InlineKeyboardButton("Unit Converter", callback_data="unit_converter")])
    else:
        keyboard.append([InlineKeyboardButton("Unit Converter", callback_data="disabled_unit_converter")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Calculator Menu", reply_markup=reply_markup)
    
def get_sci_cal_back_menu():
    # Fetch settings from MongoDB
    basic_cal_enabled = get_env_var_from_db('CALCULATOR_PLUGIN') == 'True'
    sci_cal_enabled = get_env_var_from_db('SCI_CALCULATOR_PLUGIN') == 'True'
    unit_converter_enabled = get_env_var_from_db('UNIT_CONVERTER_PLUGIN') == 'True'

    # Create buttons based on the settings
    keyboard = []

    # Basic Calculator Button
    if basic_cal_enabled:
        keyboard.append([InlineKeyboardButton("Basic Calculator", callback_data="show_calculator")])
    else:
        keyboard.append([InlineKeyboardButton("Basic Calculator", callback_data="disabled_calculator")])

    # Scientific Calculator Button
    if sci_cal_enabled:
        keyboard.append([InlineKeyboardButton("Scientific Calculator", callback_data="show_scientific_calculator")])
    else:
        keyboard.append([InlineKeyboardButton("Scientific Calculator", callback_data="disabled_sci_calculator")])

    # Unit Converter Button
    if unit_converter_enabled:
        keyboard.append([InlineKeyboardButton("Unit Converter", callback_data="unit_converter")])
    else:
        keyboard.append([InlineKeyboardButton("Unit Converter", callback_data="disabled_unit_converter")])

    return InlineKeyboardMarkup(keyboard)

def show_calculator(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    logger.info(f"User {user_id} started the Basic Calculator 👶 in chat {chat_id}")

    # Save the user_id with the chat_id and message_id as the key
    calculator_state[(chat_id, message_id)] = {"user_id": user_id, "expression": ""}

    query.answer()
    # Display the calculator with its inline buttons
    query.edit_message_text("0", reply_markup=get_keyboard())

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific calculator instance
    cal_state = calculator_state.get((chat_id, message_id), {})

    # Handle disabled basic calculator message
    if query.data == "disabled_calculator":
        query.answer(text="Calculator Plugin Disabled by the person who deployed this Echo Variant", show_alert=True)
        return  

    # Handle disabled scientific calculator message
    if query.data == "disabled_sci_calculator":
        query.answer(text="Scientific Calculator Plugin Disabled by the person who deployed this Echo Variant", show_alert=True)
        return  

    # Handle disabled Unit Converter message
    if query.data == "disabled_unit_converter":
        query.answer(text="Unit Converter Plugin Disabled by the person who deployed this Echo Variant", show_alert=True)
        return

    # Check if the user who clicked is the same as the user who initiated the calculator
    if user_id != cal_state.get("user_id"):
        # If not, show an alert and return
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use calculator(s)", show_alert=True)
        return  

    # Handling new button actions
    if query.data == "basic_cal_close":
        # Delete the calculator message
        query.message.delete()
        return
    elif query.data == "basic_cal_back":
        # Edit the current message to show the Calculator Menu
        keyboard = get_sci_cal_back_menu()  # Use the function to generate the menu keyboard
        query.edit_message_text("Calculator Menu", reply_markup=keyboard)
        return

    # Existing code for handling calculator button presses
    expression = cal_state.get("expression", "")
    if query.data == "backspace":
        expression = expression[:-1]  
    elif query.data == "AC":
        expression = ""  
    elif query.data == "+/-":
        expression = toggle_sign(expression)
    elif query.data == "%":
        expression = percentage(expression)
    elif query.data == "=":
        result = calculate(expression)
        query.edit_message_text(f"{expression}\n={result}", reply_markup=get_keyboard())
        return  # Exit the function after showing the result
    else:
        # Append the pressed button to the expression
        expression += query.data if expression != "0" else query.data.lstrip("0")

    # Update the state with the new expression
    calculator_state[(chat_id, message_id)]["expression"] = expression

    # Ensure there's always a message to display
    message_text = expression if expression else "0"
    query.edit_message_text(message_text, reply_markup=get_keyboard())
    query.answer()

def toggle_sign(expression):
    # Toggle the sign of the last complete number in the expression
    if not expression or expression[-1] in '+-*/':
        return expression + '-' 
    parts = re.split(r'(\D)', expression)
    parts[-1] = str(-float(parts[-1]))
    return ''.join(parts)

def percentage(expression):
    parts = re.split(r'(\D)', expression)
    parts[-1] = str(float(parts[-1]) / 100)
    return ''.join(parts)

def calculate(expression):
    try:
        expression = expression.replace("÷", "/")
        expression = expression.replace("×", "*")
        result = aeval(expression)
        return str(result)
    except Exception as e:
        logger.error(f"Error in calculate function: {e}")
        return "Error: " + str(e)

def setup_calculator(dispatcher):    
    dispatcher.add_handler(token_system.token_filter(CommandHandler('calculator', start_calculator)))
    dispatcher.add_handler(token_system.token_filter(CommandHandler('cal', start_calculator)))
    dispatcher.add_handler(CallbackQueryHandler(button_handler, pattern='^(basic_cal_close|basic_cal_back|\d|\+|\-|/|\*|AC|\+/\-|%|=|\.|backspace)$'))
    dispatcher.add_handler(CallbackQueryHandler(show_scientific_calculator, pattern='^show_scientific_calculator$'))
    dispatcher.add_handler(CallbackQueryHandler(show_calculator, pattern='^show_calculator$'))
    dispatcher.add_handler(CallbackQueryHandler(button_handler, pattern='^disabled_calculator$'))
    dispatcher.add_handler(CallbackQueryHandler(button_handler, pattern='^disabled_sci_calculator$'))
    dispatcher.add_handler(CallbackQueryHandler(button_handler, pattern='^disabled_unit_converter$'))
 
    setup_unit_converter(dispatcher)
