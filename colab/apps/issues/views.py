from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

from threadedcomments.models import ThreadedComment

from issues.models import Issue, IssueContributor
from issues.forms import IssueForm, InviteContributorForm, ResolutionForm
from wikis.models import Wiki

from threadedcomments.forms import RichCommentForm

@login_required
def create(request, form_class=IssueForm, template_name="issues/create.html"):
    issue_form = form_class(request.POST or None, auto_id='new_issue_%s')
    
    if issue_form.is_valid():
        issue = issue_form.save(commit=False)
        issue.creator = request.user
        issue.save()
        issue_form.save_m2m() # to save disciplines after commit=False
        
        issue.register_action(request.user, 'create', issue)
        
        issue_contributor = IssueContributor(issue=issue, user=request.user)
        issue.contributors.add(issue_contributor)
        issue_contributor.save()
        
        return HttpResponseRedirect(issue.get_absolute_url())
    
    return render_to_response(template_name, {
        "issue_form": issue_form,
    }, context_instance=RequestContext(request))

@login_required
def edit(request, slug=None, form_class=IssueForm, template_name="issues/edit.html"):
    issue = get_object_or_404(Issue, slug=slug)
    
    if issue.creator != request.user:
        return render_to_response('issues/forbidden.html', {}, context_instance=RequestContext(request))
    
    issue_form = form_class(request.POST or None, instance=issue, auto_id='edit_issue_%s')
    
    if issue_form.is_valid():
        issue = issue_form.save()
        
        issue.register_action(request.user, 'edit', issue)
        
        return HttpResponseRedirect(issue.get_absolute_url())
    
    return render_to_response(template_name, {
        'issue': issue,
        'issue_form': issue_form,
    }, context_instance=RequestContext(request))

@login_required
def delete(request, slug=None, redirect_url=None):
    issue = get_object_or_404(Issue, slug=slug)
    redirect_url = issue.get_absolute_url()
    
    if request.user == issue.creator:
        if not Wiki.objects.get_for_object(issue).exists():
            if not ThreadedComment.objects.get_for_object(issue).exists():
                issue.feed.delete()
                issue.delete()
                messages.add_message(request, messages.SUCCESS,
                    _("Issue %s deleted.") % issue.title
                )
                redirect_url = reverse("issue_list")
            else:
                messages.add_message(request, messages.ERROR,
                    _("Please delete comments before deleting the issue.")
                )
        else:
            messages.add_message(request, messages.SUCCESS,
                _("Please delete wikis before deleting the issue.")
            )
    else:
        messages.add_message(request, messages.SUCCESS,
            _("You are not the creator of this issue.")
        )
    
    return HttpResponseRedirect(redirect_url)

def issues(request, mine=False, template_name="issues/issues.html"):
    authenticated = request.user.is_authenticated()
    
    if authenticated and mine:
        issues = Issue.objects.filter(contributor_users=request.user)
    else:
        issues = Issue.objects.filter(private=False)
    
    search_terms = request.GET.get('search', '')
    if search_terms:
        issues = (issues.filter(title__icontains=search_terms) |
            issues.filter(description__icontains=search_terms))
    
    # Figure out sorting to replace the title
    list_title = ''
    if mine:
        list_title += 'My '
    
    sort = request.GET.get('sort', 'created')
    direction = request.GET.get('dir', 'desc')
    
    if sort == 'created' and direction == 'desc':
        list_title += 'Newest Issues'
        issues = issues.order_by('-created')
    if sort == 'created' and direction == 'asc':
        list_title += 'Oldest Issues'
        issues = issues.order_by('created')
    if sort == 'yeas' and direction == 'desc':
        list_title += 'Most Liked Issues'
        issues = issues.order_by('-yeas')
    if sort == 'yeas' and direction == 'asc':
        list_title += 'Least Liked Issues'
        issues = issues.order_by('yeas')
    if sort == 'nays' and direction == 'desc':
        list_title += 'Most Disliked Issues'
        issues = issues.order_by('-nays')
    if sort == 'nays' and direction == 'asc':
        list_title += 'Least Disliked Issues'
        issues = issues.order_by('nays')
    
    return render_to_response(template_name, {
        'issues': issues,
        'mine': mine,
        'search_terms': search_terms,
        'sort': sort,
        'direction': direction,
        'list_title': list_title,
    }, context_instance=RequestContext(request))

def issue(request, slug=None, template_name="issues/issue.html"):
    issue = get_object_or_404(Issue, slug=slug)
    
    # check if private
    if issue.private and not issue.user_can_read(request.user):
        return render_to_response('issues/forbidden.html', {}, context_instance=RequestContext(request))
    
    issue_type = ContentType.objects.get_for_model(issue)
    
    comment_form = RichCommentForm(auto_id='new_issue_comment_%s')
    
    return render_to_response(template_name, {
        'issue': issue,
        'comment_form': comment_form,
    }, context_instance=RequestContext(request))

@login_required
def resolve(request, slug=None, template_name="issues/resolve.html"):
    issue = get_object_or_404(Issue, slug=slug)
    
    has_papers = issue.papers.exists()
    
    resolution_form = ResolutionForm(request.POST or None, issue=issue)
    
    if resolution_form.is_valid():
        resolution = resolution_form.save()
        
        issue.register_action(request.user, 'resolve', resolution)
        
        return HttpResponseRedirect(issue.get_absolute_url())
    
    return render_to_response(template_name, {
        'issue': issue,
        'resolution_form': resolution_form,
        'has_papers': has_papers,
    }, context_instance=RequestContext(request))

@login_required
def invite(request, slug=None, form_class=InviteContributorForm, template_name="issues/invite.html"):
    issue = get_object_or_404(Issue, slug=slug)
    
    if issue.creator != request.user:
        return render_to_response('issues/forbidden.html', {}, context_instance=RequestContext(request))
    
    invite_form = form_class(request.POST or None, issue=issue)
    
    if invite_form.is_valid():
        recipients = invite_form.save()
        
        # issue.register_action(request.user, 'invite', issue)
        
        return HttpResponseRedirect(issue.get_absolute_url())
    
    return render_to_response(template_name, {
        'issue': issue,
        'invite_form': invite_form,
    }, context_instance=RequestContext(request))
