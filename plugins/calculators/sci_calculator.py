from asteval import Interpreter
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CallbackContext
import math
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Scientific Calculator state for each user
sci_calculator_state = {}

# Create an asteval interpreter instance
aeval = Interpreter()

def get_sci_keyboard(expression=""):
    # Define the scientific calculator keyboard layout
    keyboard = [
        # First row
        [InlineKeyboardButton("AC", callback_data="sci_AC"), InlineKeyboardButton("⌫", callback_data="sci_backspace"), InlineKeyboardButton("(", callback_data="sci_("), InlineKeyboardButton(")", callback_data="sci_)"), InlineKeyboardButton("π", callback_data="sci_pi"), InlineKeyboardButton("e", callback_data="sci_e"), InlineKeyboardButton("/", callback_data="sci_/")],
        # Second row
        [InlineKeyboardButton("7", callback_data="sci_7"), InlineKeyboardButton("8", callback_data="sci_8"), InlineKeyboardButton("9", callback_data="sci_9"), InlineKeyboardButton("sin", callback_data="sci_sin"), InlineKeyboardButton("cos", callback_data="sci_cos"), InlineKeyboardButton("tan", callback_data="sci_tan"), InlineKeyboardButton("*", callback_data="sci_*")],
        # Third row        
        [InlineKeyboardButton("4", callback_data="sci_4"), InlineKeyboardButton("5", callback_data="sci_5"), InlineKeyboardButton("6", callback_data="sci_6"), InlineKeyboardButton("^", callback_data="sci_**"), InlineKeyboardButton("log", callback_data="sci_log"), InlineKeyboardButton("√", callback_data="sci_sqrt"), InlineKeyboardButton("-", callback_data="sci_-")], 
        # Fourth row         
        [InlineKeyboardButton("1", callback_data="sci_1"), InlineKeyboardButton("2", callback_data="sci_2"), InlineKeyboardButton("3", callback_data="sci_3"), InlineKeyboardButton("%", callback_data="sci_percent"), InlineKeyboardButton("!", callback_data="sci_fact"), InlineKeyboardButton("+", callback_data="sci_+")],       
        # Eighth row
        [InlineKeyboardButton("0", callback_data="sci_0"), InlineKeyboardButton(".", callback_data="sci_."), InlineKeyboardButton("=", callback_data="sci_=")]
        ]
    # Nevigation Buttons Row
    additional_buttons = [
        InlineKeyboardButton("Close", callback_data="sci_close"),
        InlineKeyboardButton("Help", callback_data="sci_help"),
        InlineKeyboardButton("Back", callback_data="sci_back")
    ]
    keyboard.append(additional_buttons) 
    return InlineKeyboardMarkup(keyboard)
    
def show_scientific_calculator(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    logger.info(f"User {username} ({user_id}) started the Scientific Calculator 🧪🔬 in chat {chat_id}")

    # Save the user_id with the chat_id and message_id as the key
    sci_calculator_state[(chat_id, message_id)] = {"user_id": user_id, "expression": ""}

    query.answer()
    query.edit_message_text("Scientific Calculator", reply_markup=get_sci_keyboard())

def sci_button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    # Retrieve the state for this specific calculator instance
    sci_cal_state = sci_calculator_state.get((chat_id, message_id), {})

    # Check if the user who clicked is the same as the user who initiated the calculator
    if user_id != sci_cal_state.get("user_id"):
        query.answer(text="Mind your own business 😑. Don't disturb him. Use /cal if you want to use calculator(s)", show_alert=True)
        return

    expression = sci_cal_state.get("expression", "")

    # Handling new button actions
    if query.data == "sci_close":
        # Delete the calculator message
        query.message.delete()
        return
    elif query.data == "sci_help":
        # Send a help message with detailed explanations
        context.bot.send_message(chat_id, """<b><u>🧪🔬 Scientific Calculator Help 🧪🔬</u></b>

<i>To make the most of this scientific calculator, follow these simple steps:</i>

1. <b>Basic Arithmetic:</b>
   - <i>Addition (+):</i> To add numbers, tap the number buttons, followed by <code>+</code>, and then the next number. For example, to add 5 and 7, tap <code>5 + 7</code>.
   - <i>Subtraction (-):</i> To subtract numbers, tap the number buttons, followed by <code>-</code>, and then the next number. For example, to subtract 8 from 12, tap <code>12 - 8</code>.
   - <i>Multiplication (*):</i> To multiply numbers, tap the number buttons, followed by <code>*</code>, and then the next number. For example, to multiply 3 by 4, tap <code>3 * 4</code>.
   - <i>Division (/):</i> To divide numbers, tap the number buttons, followed by <code>/</code>, and then the next number. For example, to divide 10 by 2, tap <code>10 / 2</code>.
   - <i>Decimal (.):</i> To input decimal numbers, tap the <code>.</code> button. For example, for 1.5, tap <code>1 . 5</code>.

2. <b>Math Functions:</b>
   - <i>Sine (sin):</i> To calculate the sine of an angle, tap <code>sin</code>, followed by the angle in radians. For example, to find the sine of 30 degrees, tap <code>sin(30)</code>.
   - <i>Cosine (cos):</i> To calculate the cosine of an angle, tap <code>cos</code>, followed by the angle in radians. For example, to find the cosine of 45 degrees, tap <code>cos(45)</code>.
   - <i>Tangent (tan):</i> To calculate the tangent of an angle, tap <code>tan</code>, followed by the angle in radians. For example, to find the tangent of 60 degrees, tap <code>tan(60)</code>.
   - <i>Logarithm (log):</i> To calculate the logarithm of a number, tap <code>log</code>, followed by the number. For example, to find the logarithm of 100, tap <code>log(100)</code>.
   - <i>Square Root (√):</i> To calculate the square root of a number, tap <code>√</code>, followed by the number. For example, to find the square root of 25, tap <code>√(25)</code>.
   - <i>Exponentiation (^):</i> To calculate the power of a number, tap the base number, followed by <code>^</code>, and then the exponent. For example, to calculate 2^3, tap <code>2^3</code>.

3. <b>Constants:</b>
   - <i>Pi (π):</i> To use the constant pi (π), simply tap <code>π</code> where needed in your calculations.
   - <i>Euler's Number (e):</i> To use Euler's number (e), simply tap <code>e</code> where needed in your calculations.

4. <b>Percentages (%)</b>
   - To convert a number to a percentage, simply input the number and then tap <code>%</code>. For example, to convert 0.25 to a percentage, tap <code>0.25 %</code>.
   
5. <b>Clearing:</b>
   - Reset the calculator with <code>AC</code>.
   - Remove the last character using <code>⌫</code>.
   
6. <b>Result:</b>
   - Tap <code>=</code> to view the calculated result.
   
7. <b>Navigation:</b>
   - To go back, tap <code>Back</code>.
   - For more assistance, hit the <code>Help</code> button again.
   - To exit, press <code>Close</code>.
   
Now, you're all set to perform scientific calculations with ease! 📚🔍
<i>Note:</i> Ensure correct expression entry and use parentheses for complex calculations. Dive into the world of math and science!
""",
        parse_mode="HTML",
    )
        return
    elif query.data == "sci_back":
        from plugins.calculators.calculator import get_sci_cal_back_menu
        # Edit the current message to show the Calculator Menu
        keyboard = get_sci_cal_back_menu()  
        query.edit_message_text("Calculator Menu", reply_markup=keyboard)
        return

    # If AC or backspace is pressed, handle those separately
    if query.data == "sci_AC":
        expression = ""  # Clear the expression
    elif query.data == "sci_backspace":
        expression = expression[:-1]  # Remove the last character
    elif query.data == "sci_percent":
        # Append *1/100 to convert the last number to a percentage
        expression += "*1/100"  # Assumes expression ends with a number
    elif query.data == "sci_=":
        # Calculate the result
        result = sci_calculate(expression)
        query.edit_message_text(f"{expression}\n={result}", reply_markup=get_sci_keyboard(expression))
        sci_calculator_state[(chat_id, message_id)]["expression"] = ""  # Reset the state after calculation
        return
    else:
        # Append the appropriate symbol or function to the expression
        expression += query.data[4:]  # Remove 'sci_' prefix

    # Update the expression in the state
    sci_cal_state["expression"] = expression
    sci_calculator_state[(chat_id, message_id)] = sci_cal_state

    # Update the message text
    query.edit_message_text(expression if expression else "0", reply_markup=get_sci_keyboard(expression))
    query.answer()

def sci_calculate(expression):
    try:
        # Logging: Log the expression before replacement
        logger.info("Before replacement: %s", expression)
        # Replace the 'sci_' symbols with the actual operation to perform
        expression = re.sub(r"sci_[a-zA-Z0-9.]+", replace_symbols, expression)
        # Logging: Log the expression after replacement
        logger.info("After replacement: %s", expression)
        # Evaluate the expression using asteval
        result = aeval(expression)
        if isinstance(result, float):
            # Format the result to avoid scientific notation for large numbers
            return "{:.10g}".format(result)
        return str(result)
    except Exception as e:
        logger.error(f"Error in sci_calculate: {e}")
        return "Error: " + str(e)

def replace_symbols(match):
    symbol = match.group(0)
    if symbol == "sci_**":
        return "**"
    elif symbol == "sci_sin":
        return "sin"
    elif symbol == "sci_cos":
        return "cos"
    elif symbol == "sci_tan":
        return "tan"
    elif symbol == "sci_log":
        return "log10"  # Assumes base 10 for simplicity
    elif symbol == "sci_sqrt":
        return "sqrt"
    elif symbol == "sci_fact":
        return "factorial"
    elif symbol == "sci_pi":
        return "pi"
    elif symbol == "sci_e":
        return "e"
    elif symbol == "sci_percent":
        # Convert the last number in the expression to a percentage
        return "/100.0"
    elif symbol.startswith("sci_"):
        # Handle numbers and basic operators by stripping off 'sci_' prefix
        return symbol[4:]
    else:
        return symbol

# Add math functions to aeval's symtable for direct use
aeval.symtable['sin'] = math.sin
aeval.symtable['cos'] = math.cos
aeval.symtable['tan'] = math.tan
aeval.symtable['log10'] = math.log10
aeval.symtable['sqrt'] = math.sqrt
aeval.symtable['factorial'] = math.factorial
aeval.symtable['pi'] = math.pi
aeval.symtable['e'] = math.e
aeval.symtable['**'] = pow  # For power calculations

def sci_calculator_disabled(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer(text="Scientific Calculator Plugin Disabled by the person who deployed this Echo Variant", show_alert=True)

def setup_sci_calculator(dispatcher):
    # Register handlers for the scientific calculator
    dispatcher.add_handler(CallbackQueryHandler(sci_button_handler, pattern='^sci_.*$'))
    dispatcher.add_handler(CallbackQueryHandler(sci_calculator_disabled, pattern='^disabled_sci_calculator$'))

# This would be called from the main bot file to setup the scientific calculator handlers
# from plugins.calculators.sci_calculator import setup_sci_calculator
# setup_sci_calculator(dispatcher)
