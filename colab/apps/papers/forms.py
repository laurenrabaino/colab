from django import forms
from django.forms import widgets
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from papers.models import Paper
from tinymce.widgets import TinyMCE

class PaperForm(forms.ModelForm):
    
    content = forms.CharField(widget=TinyMCE)
    comment = forms.CharField(required=False, max_length=255)
    
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        widget=TinyMCE)
    object_id = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Paper
        fields = ['summarized', 'content', 'tags', 'content_type', 'object_id']
    
    def __init__(self, *args, **kwargs):
        super(PaperForm, self).__init__(*args, **kwargs)

    def save(self):
        # 1 - Get the old stuff before saving
        if self.instance.id is None:
            old_content = ''
            new = True
        else:
            old_content = self.instance.content
            new = False
        comment = self.cleaned_data["comment"]

        # 2 - Save the page
        paper = super(PaperForm, self).save()

        # 3 - Set creator and group
        editor = getattr(self, 'editor', None)
        content_object = getattr(self, 'content_object', None)
        if new:
            if editor is not None:
                paper.creator = editor
                paper.content_object = content_object
            paper.save()

        # 4 - Create new revision
        revision = paper.new_revision(old_content, comment, editor)

        return paper, revision
