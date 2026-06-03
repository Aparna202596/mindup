from apps.users.models import CustomUser

from apps.topics.models import Topic

from apps.categories.models import Category

from apps.questions.models import Question

def get_dashboard_stats():

    return {

        "users":
            CustomUser.objects.count(),

        "topics":
            Topic.objects.count(),

        "categories":
            Category.objects.count(),

        "questions":
            Question.objects.count(),
    }