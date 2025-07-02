"""
Edit Question Plugin

This plugin implements functionality to edit questions in existing surveys.
It allows administrators to modify question text, options, and other properties.
"""

from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Replace deprecated database imports with db_manager helpers
from core.db_manager import (
    DATABASE,
    get_all_polls,
    get_poll_id_by_name,
    get_poll_by_id,
    get_questions_by_poll,
)
import sqlite3
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    """Check if a user is an administrator."""
    return user_id in ADMIN_IDS


async def get_surveys(creator_id: Optional[int] = None) -> List[Dict]:
    """Return a list of all surveys."""
    surveys = []
    for name in get_all_polls():
        poll_id = get_poll_id_by_name(name)
        poll = get_poll_by_id(poll_id)
        if not poll:
            continue
        poll_data = {
            "id": poll_id,
            "title": poll["name"],
            "questions": get_questions_by_poll(poll_id),
            "time_limit": poll.get("time_limit"),
        }
        surveys.append(poll_data)
    return surveys


async def get_survey_by_id(survey_id: int) -> Optional[Dict]:
    """Fetch a survey by its ID."""
    poll = get_poll_by_id(survey_id)
    if not poll:
        return None
    poll["title"] = poll.pop("name")
    poll["questions"] = get_questions_by_poll(survey_id)
    return poll


async def update_question(survey_id: int, question_index: int, question: Dict) -> bool:
    """Update a question in the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM questions WHERE poll_id = ? ORDER BY id LIMIT 1 OFFSET ?",
        (survey_id, question_index),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    question_id = row[0]
    options_str = ",".join(question.get("options", [])) if question.get("options") else None
    cursor.execute(
        "UPDATE questions SET text = ?, type = ?, options = ? WHERE id = ?",
        (question.get("text"), question.get("type"), options_str, question_id),
    )
    conn.commit()
    conn.close()
    return True


class EditQuestionStates(StatesGroup):
    """States for editing questions"""
    SelectSurvey = State()
    SelectQuestion = State()
    EditQuestionText = State()
    EditQuestionOptions = State()
    AddOption = State()
    RemoveOption = State()
    ConfirmChanges = State()


class EditQuestionPlugin:
    """Plugin for editing questions in surveys"""
    
    def __init__(self):
        self.name = "edit_question"
        self.description = "Edit questions in existing surveys"
        
    async def register_handlers(self, dp: Dispatcher):
        """Register all handlers for this plugin"""
        dp.message.register(
            self.cmd_edit_question,
            Command("edit_question"),
            lambda msg: is_admin(msg.from_user.id)
        )
        
        dp.callback_query.register(
            self.handle_survey_selection,
            lambda c: c.data.startswith('edit_survey_'),
            StateFilter(EditQuestionStates.SelectSurvey)
        )
        
        dp.callback_query.register(
            self.handle_question_selection,
            lambda c: c.data.startswith('edit_question_'),
            StateFilter(EditQuestionStates.SelectQuestion)
        )
        
        dp.callback_query.register(
            self.handle_edit_action,
            lambda c: c.data.startswith('edit_action_'),
            StateFilter(
                EditQuestionStates.SelectQuestion,
                EditQuestionStates.EditQuestionText,
                EditQuestionStates.EditQuestionOptions,
                EditQuestionStates.ConfirmChanges
            )
        )
        
        dp.message.register(
            self.process_question_text,
            StateFilter(EditQuestionStates.EditQuestionText)
        )
        
        dp.message.register(
            self.process_new_option,
            StateFilter(EditQuestionStates.AddOption)
        )
        
        dp.callback_query.register(
            self.handle_remove_option,
            lambda c: c.data.startswith('remove_option_'),
            StateFilter(EditQuestionStates.RemoveOption)
        )
        
    def get_commands(self):
        """Return a list of commands this plugin provides"""
        return [
            {"command": "edit_question", "description": "Edit questions in existing surveys"}
        ]
        
    def get_keyboards(self):
        """Return any keyboards this plugin needs"""
        return {}
        
    def get_states(self):
        """Return any states this plugin uses"""
        return EditQuestionStates
    
    async def cmd_edit_question(self, message: types.Message, state: FSMContext):
        """Handle the /edit_question command"""
        user_id = message.from_user.id
        
        # Get surveys created by this admin
        surveys = await get_surveys(creator_id=user_id)
        
        if not surveys:
            await message.answer("You don't have any surveys to edit.")
            return
            
        # Create a keyboard with survey options
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        for survey in surveys:
            keyboard.add(InlineKeyboardButton(
                text=survey['title'],
                callback_data=f"edit_survey_{survey['id']}"
            ))
            
        await message.answer("Select a survey to edit questions:", reply_markup=keyboard)
        await EditQuestionStates.SelectSurvey.set()
        
    async def handle_survey_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle selection of a survey to edit"""
        survey_id = int(callback_query.data.split('_')[2])
        survey = await get_survey_by_id(survey_id)
        
        if not survey:
            await callback_query.answer("Survey not found.")
            return
            
        # Store the selected survey in state
        await state.update_data(selected_survey=survey)
        
        # Get questions for this survey
        questions = survey.get('questions', [])
        
        if not questions:
            await callback_query.message.edit_text(
                "This survey doesn't have any questions to edit.",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(text="Back", callback_data="edit_action_back_to_surveys")
                )
            )
            return
            
        # Create a keyboard with question options
        keyboard = InlineKeyboardMarkup(row_width=1)
        
        for i, question in enumerate(questions):
            keyboard.add(InlineKeyboardButton(
                text=f"Q{i+1}: {question['text'][:30]}...",
                callback_data=f"edit_question_{i}"
            ))
            
        keyboard.add(InlineKeyboardButton(
            text="Back",
            callback_data="edit_action_back_to_surveys"
        ))
        
        await callback_query.message.edit_text(
            f"Select a question to edit from survey '{survey['title']}':",
            reply_markup=keyboard
        )
        await EditQuestionStates.SelectQuestion.set()
        await callback_query.answer()
        
    async def handle_question_selection(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle selection of a question to edit"""
        question_index = int(callback_query.data.split('_')[2])
        
        # Get the survey from state
        state_data = await state.get_data()
        survey = state_data.get('selected_survey')
        
        if not survey or question_index >= len(survey.get('questions', [])):
            await callback_query.answer("Question not found.")
            return
            
        question = survey['questions'][question_index]
        
        # Store the selected question in state
        await state.update_data(
            selected_question=question,
            question_index=question_index
        )
        
        # Show question details and edit options
        await self.show_question_edit_menu(callback_query.message, question)
        await callback_query.answer()
        
    async def show_question_edit_menu(self, message: types.Message, question: dict):
        """Show the edit menu for a question"""
        # Format question details
        question_text = question['text']
        question_type = question['type']
        
        details = f"<b>Question:</b> {question_text}\n<b>Type:</b> {question_type}\n"
        
        if 'options' in question and question['options']:
            details += "\n<b>Options:</b>\n"
            for i, option in enumerate(question['options']):
                details += f"{i+1}. {option}\n"
                
        # Create edit action buttons
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton(
                text="Edit Question Text",
                callback_data="edit_action_text"
            ),
            InlineKeyboardButton(
                text="Edit Options",
                callback_data="edit_action_options"
            ),
            InlineKeyboardButton(
                text="Back to Questions",
                callback_data="edit_action_back_to_questions"
            )
        )
        
        await message.edit_text(
            details,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def handle_edit_action(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle edit actions for a question"""
        action = callback_query.data.split('_')[2]
        
        if action == "text":
            await callback_query.message.edit_text(
                "Please enter the new text for this question:",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(text="Cancel", callback_data="edit_action_cancel")
                )
            )
            await EditQuestionStates.EditQuestionText.set()
            
        elif action == "options":
            # Show options edit menu
            state_data = await state.get_data()
            question = state_data.get('selected_question')
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton(text="Add Option", callback_data="edit_action_add_option"),
                InlineKeyboardButton(text="Remove Option", callback_data="edit_action_remove_option"),
                InlineKeyboardButton(text="Back", callback_data="edit_action_back")
            )
            
            options_text = "Current options:\n"
            if 'options' in question and question['options']:
                for i, option in enumerate(question['options']):
                    options_text += f"{i+1}. {option}\n"
            else:
                options_text += "No options defined."
                
            await callback_query.message.edit_text(
                options_text,
                reply_markup=keyboard
            )
            await EditQuestionStates.EditQuestionOptions.set()
            
        elif action == "add_option":
            await callback_query.message.edit_text(
                "Please enter the new option text:",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(text="Cancel", callback_data="edit_action_cancel_option")
                )
            )
            await EditQuestionStates.AddOption.set()
            
        elif action == "remove_option":
            # Show remove option menu
            state_data = await state.get_data()
            question = state_data.get('selected_question')
            
            if not question.get('options'):
                await callback_query.message.edit_text(
                    "This question doesn't have any options to remove.",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton(text="Back", callback_data="edit_action_back")
                    )
                )
                return
                
            keyboard = InlineKeyboardMarkup(row_width=1)
            
            for i, option in enumerate(question['options']):
                keyboard.add(InlineKeyboardButton(
                    text=f"Remove: {option}",
                    callback_data=f"remove_option_{i}"
                ))
                
            keyboard.add(InlineKeyboardButton(
                text="Cancel",
                callback_data="edit_action_cancel_option"
            ))
            
            await callback_query.message.edit_text(
                "Select an option to remove:",
                reply_markup=keyboard
            )
            await EditQuestionStates.RemoveOption.set()
            
        elif action == "back":
            # Go back to question details
            state_data = await state.get_data()
            question = state_data.get('selected_question')
            await self.show_question_edit_menu(callback_query.message, question)
            
        elif action == "back_to_questions":
            # Go back to question selection
            await self.handle_survey_selection(callback_query, state)
            
        elif action == "back_to_surveys":
            # Go back to survey selection
            await self.cmd_edit_question(callback_query.message, state)
            
        elif action == "cancel":
            # Cancel editing and go back to question details
            state_data = await state.get_data()
            question = state_data.get('selected_question')
            await self.show_question_edit_menu(callback_query.message, question)
            
        elif action == "cancel_option":
            # Cancel option editing and go back to options menu
            # Create a new callback with the options action
            await self.handle_edit_action(
                types.CallbackQuery(
                    id=callback_query.id,
                    from_user=callback_query.from_user,
                    chat_instance=callback_query.chat_instance,
                    message=callback_query.message,
                    data="edit_action_options"
                ),
                state
            )
            
        elif action == "save":
            # Save changes to the question
            state_data = await state.get_data()
            survey = state_data.get('selected_survey')
            question = state_data.get('selected_question')
            question_index = state_data.get('question_index')
            
            # Update the question in the database
            survey['questions'][question_index] = question
            # Update the question in the database
            success = await update_question(survey['id'], question_index, question)
            
            if success:
                await callback_query.message.edit_text(
                    "Question updated successfully!",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton(text="Back to Questions", callback_data="edit_action_back_to_questions")
                    )
                )
            else:
                await callback_query.message.edit_text(
                    "Failed to update question. Please try again.",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton(text="Back", callback_data="edit_action_back")
                    )
                )
                
        await callback_query.answer()
        
    async def process_question_text(self, message: types.Message, state: FSMContext):
        """Process new question text input"""
        new_text = message.text.strip()
        
        if not new_text:
            await message.answer("Question text cannot be empty. Please try again.")
            return
            
        # Update question text in state
        state_data = await state.get_data()
        question = state_data.get('selected_question')
        question['text'] = new_text
        
        await state.update_data(selected_question=question)
        
        # Show confirmation
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="Save Changes", callback_data="edit_action_save"),
            InlineKeyboardButton(text="Cancel", callback_data="edit_action_cancel")
        )
        
        await message.answer(
            f"Question text updated to:\n\n{new_text}\n\nDo you want to save these changes?",
            reply_markup=keyboard
        )
        await EditQuestionStates.ConfirmChanges.set()
        
    async def process_new_option(self, message: types.Message, state: FSMContext):
        """Process new option input"""
        new_option = message.text.strip()
        
        if not new_option:
            await message.answer("Option text cannot be empty. Please try again.")
            return
            
        # Update options in state
        state_data = await state.get_data()
        question = state_data.get('selected_question')
        
        if 'options' not in question:
            question['options'] = []
            
        question['options'].append(new_option)
        await state.update_data(selected_question=question)
        
        # Show confirmation
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(text="Save Changes", callback_data="edit_action_save"),
            InlineKeyboardButton(text="Add Another Option", callback_data="edit_action_add_option"),
            InlineKeyboardButton(text="Cancel", callback_data="edit_action_cancel")
        )
        
        options_text = "Updated options:\n"
        for i, option in enumerate(question['options']):
            options_text += f"{i+1}. {option}\n"
            
        await message.answer(
            f"{options_text}\n\nDo you want to save these changes or add another option?",
            reply_markup=keyboard
        )
        await EditQuestionStates.ConfirmChanges.set()
        
    async def handle_remove_option(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle removal of an option"""
        option_index = int(callback_query.data.split('_')[2])
        
        # Update options in state
        state_data = await state.get_data()
        question = state_data.get('selected_question')
        
        if 'options' in question and 0 <= option_index < len(question['options']):
            removed_option = question['options'].pop(option_index)
            await state.update_data(selected_question=question)
            
            # Show confirmation
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton(text="Save Changes", callback_data="edit_action_save"),
                InlineKeyboardButton(text="Remove Another Option", callback_data="edit_action_remove_option"),
                InlineKeyboardButton(text="Cancel", callback_data="edit_action_cancel")
            )
            
            options_text = "Updated options:\n"
            if question['options']:
                for i, option in enumerate(question['options']):
                    options_text += f"{i+1}. {option}\n"
            else:
                options_text += "No options remaining."
                
            await callback_query.message.edit_text(
                f"Removed option: {removed_option}\n\n{options_text}\n\nDo you want to save these changes or remove another option?",
                reply_markup=keyboard
            )
            await EditQuestionStates.ConfirmChanges.set()
        else:
            await callback_query.answer("Invalid option index.")


# This function is required for the plugin manager to load the plugin
def load_plugin():
    """Load the plugin"""
    return EditQuestionPlugin()
