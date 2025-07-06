class ResponseMixin:
    def _add_or_update_response(self, survey, user_id, question_id, new_response):
        """Add or update a response in the survey."""
        if survey.get('is_anonymous'):
            survey['responses'].append(new_response)
            return
        for i, response in enumerate(survey['responses']):
            if response.get('user_id') == user_id and response.get('question_id') == question_id:
                survey['responses'][i] = new_response
                return
        survey['responses'].append(new_response)
