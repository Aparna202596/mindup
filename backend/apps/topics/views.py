from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView

from django.urls import reverse_lazy

from apps.topics.models import Topic

from apps.topics.forms import TopicForm

from django.views.generic import ListView, DetailView

class TopicCreateView(
        LoginRequiredMixin,
        CreateView
):

    model = Topic

    form_class = TopicForm

    template_name = "topics/topic_create.html"

    success_url = reverse_lazy("topic-list")

    def form_valid(self, form):

        form.instance.created_by = self.request.user

        return super().form_valid(form)
    
class TopicListView(ListView):

    model = Topic

    template_name = "topics/topic_list.html"

    paginate_by = 10

    context_object_name = "topics"

    queryset = Topic.objects.filter(
        status="approved"
    )

class TopicDetailView(DetailView):

    model = Topic

    template_name = "topics/topic_detail.html"