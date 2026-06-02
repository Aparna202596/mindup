from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser
from apps.questions.models import Question


class Answer(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")

    content = models.TextField()

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    is_approved = models.BooleanField(default=True)  # auto publish

    def __str__(self):
        return self.content[:50]
    
class AnswerPoint(TimeStampedModel):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="points")

    point = models.TextField()

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.point[:50]