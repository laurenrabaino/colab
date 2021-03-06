from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType

def create_actions(model, **kwargs):
    try:
        content_type = ContentType.objects.get_for_model(model)

        create_action = models.Action(content_type=content_type, action='create', description='created', slug='create')
        create_action.save()
        edit_action = models.Action(content_type=content_type, action='edit', description='edited', slug='edit')
        edit_action.save()
        comment_action = models.Action(content_type=content_type, action='comment', description='commented on', slug='comment')
        comment_action.save()
    except:
        print "Skipping creation of default actions as ContentType instances not found"
