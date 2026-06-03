from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    CreateView,
    ListView,
    DetailView
)

from django.shortcuts import redirect

from .models import Question
from .forms import QuestionForm

from .services.question_service import create_question

class QuestionCreateView(
    LoginRequiredMixin,
    CreateView
):
    form_class = QuestionForm
    template_name = "questions/question_create.html"

    def form_valid(self, form):

        result = create_question(
            user=self.request.user,
            subcategory=form.cleaned_data["subcategory"],
            title=form.cleaned_data["title"]
        )

        if not result["success"]:

            form.add_error(
                "title",
                "Similar question already exists."
            )

            return self.form_invalid(form)

        return redirect(
            "question-detail",
            pk=result["question"].pk
        )


class QuestionListView(ListView):
    model = Question
    template_name = "questions/question_list.html"
    context_object_name = "questions"
    paginate_by = 10


class QuestionDetailView(DetailView):
    model = Question
    template_name = "questions/question_detail.html"

    def get_object(self):
        obj = super().get_object()

        obj.view_count += 1
        obj.save(update_fields=["view_count"])

        return obj