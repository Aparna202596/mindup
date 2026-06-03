from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    CreateView,
    DetailView,
    ListView
)

from django.urls import reverse_lazy

from .models import (
    Answer,
    AnswerPoint
)

from .forms import (
    AnswerForm,
    AnswerPointForm
)

class AnswerCreateView(
    LoginRequiredMixin,
    CreateView
):
    model = Answer
    form_class = AnswerForm
    template_name = "answers/answer_create.html"
    success_url = reverse_lazy("question-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AnswerListView(ListView):
    model = Answer
    template_name = "answers/answer_list.html"
    paginate_by = 10


class AnswerDetailView(DetailView):
    model = Answer
    template_name = "answers/answer_detail.html"


class AnswerPointCreateView(
    LoginRequiredMixin,
    CreateView
):
    model = AnswerPoint
    form_class = AnswerPointForm
    template_name = "answers/answerpoint_create.html"
    success_url = reverse_lazy("answer-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class AnswerPointListView(ListView):
    model = AnswerPoint
    template_name = "answers/answerpoint_list.html"
    paginate_by = 10