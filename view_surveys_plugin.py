"""
View Surveys Plugin

This plugin implements the functionality to view surveys in the system.
It allows users to list, filter, and view details of surveys.
"""

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_surveys, get_survey_by_id
from utils import format_survey_info, has_poll_ended


class ViewSurveysStates(StatesGroup):
    """States for viewing surveys"""
    Viewing = State()
    FilterMenu = State()
    ViewingDetails = State()


class ViewSurveysPlugin:
    """Plugin for viewing surveys"""
    
    def __init__(self):
        self.name = "view_surveys"
        self.description = "View and manage surveys"
        
    async def register_handlers(self, dp: Dispatcher):
        """Register all handlers for this plugin"""
        dp.register_message_handler(self.cmd_view_surveys, commands=["view_surveys"])
        dp.register_callback_query_handler(
            self.handle_survey_selection, 
            lambda c: c.data.startswith('view_survey_'),
            state=ViewSurveysStates.Viewing
        )
        dp.register_callback_query_handler(
            self.handle_filter_selection,
            lambda c: c.data.startswith('filter_'),
            state=ViewSurveysStates.FilterMenu
        )
        dp.register_callback_query_handler(
            self.handle_survey_action,
            lambda c: c.data.startswith('survey_action_'),
            state=ViewSurveysStates.ViewingDetails
        )
        
    def get_commands(self):
        """Return a list of commands this plugin provides"""
        return [
            {"command": "view_surveys", "description": "View available surveys"}
        ]
        
    def get_keyboards(self):
        """Return any keyboards this plugin needs"""
        return {}
        
    def get_states(self):
        """Return any states this plugin uses"""
        return ViewSurveysStates
    
    async def cmd_view_surveys(self, message: types.Message, state: FSMContext):
        """Handle the /view_surveys command"""
        user_id = message.from_user.id
        surveys = await get_surveys(user_id=user_id)
        
        if not surveys:
            await message.answer("No surveys available.")
            return
            
        # Create a keyboard with survey options
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        for survey in surveys:
            status = "✅ Active" if not has_poll_ended(survey) else "❌ Ended"
            button_text = f"{survey['title']} ({status})"
            keyboard.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_survey_{survey['id']}"
            ))
            
        # Add filter button
        keyboard.add(InlineKeyboardButton(
            text="🔍 Filter Surveys",
            callback_data="filter_menu"
        ))
        
        await message.answer("Available surveys:", reply_markup=keyboard)
        await ViewSurveysStates.Viewing.set()
        
    async def handle_survey_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle selection of a survey from the list"""
        survey_id = int(callback_query.data.split('_')[2])
        survey = await get_survey_by_id(survey_id)
        
        if not survey:
            await callback_query.answer("Survey not found.")
            return
            
        # Format survey details
        survey_info = await format_survey_info(survey)
        
        # Create action buttons
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # Add appropriate action buttons based on survey status
        if not has_poll_ended(survey):
            keyboard.add(InlineKeyboardButton(
                text="Take Survey",
                callback_data=f"survey_action_take_{survey_id}"
            ))
            
        # Add back button
        keyboard.add(InlineKeyboardButton(
            text="Back to List",
            callback_data="survey_action_back"
        ))
        
        await callback_query.message.edit_text(
            survey_info,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await ViewSurveysStates.ViewingDetails.set()
        await callback_query.answer()
        
    async def handle_filter_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle filter selection for surveys"""
        user_id = callback_query.from_user.id
        filter_type = callback_query.data.split('_')[1]
        
        if filter_type == "menu":
            # Show filter options
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton(text="Active Surveys", callback_data="filter_active"),
                InlineKeyboardButton(text="Completed Surveys", callback_data="filter_completed"),
                InlineKeyboardButton(text="All Surveys", callback_data="filter_all"),
                InlineKeyboardButton(text="Back", callback_data="filter_back")
            )
            await callback_query.message.edit_text(
                "Select filter option:",
                reply_markup=keyboard
            )
            await ViewSurveysStates.FilterMenu.set()
            
        elif filter_type == "back":
            # Go back to main survey list
            await self.cmd_view_surveys(callback_query.message, state)
            
        else:
            # Apply selected filter
            surveys = await get_surveys(user_id=user_id)
            
            if filter_type == "active":
                surveys = [s for s in surveys if not has_poll_ended(s)]
            elif filter_type == "completed":
                surveys = [s for s in surveys if has_poll_ended(s)]
                
            # Create keyboard with filtered surveys
            keyboard = InlineKeyboardMarkup(row_width=1)
            
            if not surveys:
                await callback_query.message.edit_text(
                    "No surveys match your filter.",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton(text="Back", callback_data="filter_menu")
                    )
                )
                return
                
            for survey in surveys:
                status = "✅ Active" if not has_poll_ended(survey) else "❌ Ended"
                button_text = f"{survey['title']} ({status})"
                keyboard.add(InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"view_survey_{survey['id']}"
                ))
                
            # Add filter button
            keyboard.add(InlineKeyboardButton(
                text="🔍 Filter Surveys",
                callback_data="filter_menu"
            ))
            
            await callback_query.message.edit_text(
                f"Surveys ({filter_type}):",
                reply_markup=keyboard
            )
            await ViewSurveysStates.Viewing.set()
            
        await callback_query.answer()
        
    async def handle_survey_action(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle actions on a specific survey"""
        action = callback_query.data.split('_')[2]
        
        if action == "back":
            # Go back to survey list
            await self.cmd_view_surveys(callback_query.message, state)
            
        elif action == "take":
            survey_id = int(callback_query.data.split('_')[3])
            # Start the survey taking process
            # This would typically transition to another plugin's state
            await callback_query.message.answer(f"Starting survey {survey_id}...")
            # Reset state to allow other handlers to take over
            await state.finish()
            
        await callback_query.answer()


# This function is required for the plugin manager to load the plugin
def load_plugin():
    """Load the plugin"""
    return ViewSurveysPlugin()
