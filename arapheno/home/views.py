from django.shortcuts import redirect, render
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm

from arapheno.settings.private_settings import REQUIRE_USER_AUTHENTICATION
from decorators import login_if_required
from forms import GlobalSearchForm, RNASeqGlobalSearchForm

from phenotypedb.models import Study, Phenotype, Accession, OntologyTerm, RNASeq
from phenotypedb.tables import PhenotypeTable, StudyTable, AccessionTable, OntologyTermTable, RNASeqTable, RNASeqStudyTable

from django.db.models import Count
from django_tables2 import RequestConfig

# Base context for all views: whether to show the main menu bar
def authentication_context(request) :
    return { 'show_menu_bar': request.user.is_authenticated or not REQUIRE_USER_AUTHENTICATION }

'''
Login View of ArachisPheno
'''
def login_request(request) :
    errmsg = None
    INVALID_USERNAME_OR_PASSWORD = 'Invalid username or password - please try again.'

    if not REQUIRE_USER_AUTHENTICATION :
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = AuthenticationForm(request = request, data = request.POST)
        if form.is_valid() :
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username = username, password = password)
            if user is not None :
                login(request, user)
                return redirect(settings.LOGIN_REDIRECT_URL)
            else :
                errmsg = 'Invalid form' #INVALID_USERNAME_OR_PASSWORD
        else :
            errmsg = INVALID_USERNAME_OR_PASSWORD

    form = AuthenticationForm()
    context = {
        'form': form,
        'errmsg': errmsg,
    }
    return render(request, 'home/login.html', context)

'''
Home View of ArachisPheno
'''
@login_if_required
def home(request):
    search_form = GlobalSearchForm()
    if "global_search-autocomplete" in request.POST:
        query = request.POST.getlist('global_search-autocomplete')[0]
        return HttpResponseRedirect("search_results/%s/"%(query))
    stats = {}
    studies = Study.objects.published().annotate(pheno_count=Count('phenotype')).annotate(rna_count=Count('rnaseq'))
    stats['studies'] = studies.filter(pheno_count__gt=0).filter(rna_count=0).count()
    stats['phenotypes_published'] = Phenotype.objects.published().count()
    stats['phenotypes'] = Phenotype.objects.all().count()
    if len(Study.objects.all()) == 0 :
        stats['last_update'] = '--'
    else :
        stats['last_update'] = Study.objects.all().order_by("-update_date")[0].update_date.strftime('%b/%d/%Y')
    context = { 'search_form': search_form, 'stats': stats, 'is_rnaseq': False }
    context.update(authentication_context(request))
    return render(request, 'home/home.html', context)

@login_if_required
def home_rnaseq(request):
    search_form = RNASeqGlobalSearchForm()
    if "rnaseq_global_search-autocomplete" in request.POST:
        query = request.POST.getlist('rnaseq_global_search-autocomplete')[0]
        print(query)
        return HttpResponseRedirect("rnaseq_search_results/%s/"%(query))
    stats = {}
    studies = Study.objects.published().annotate(pheno_count=Count('phenotype')).annotate(rna_count=Count('rnaseq'))
    stats['studies'] = studies.filter(pheno_count=0).filter(rna_count__gt=0).count()
    stats['rnaseqs'] = RNASeq.objects.all().count()
    if len(Study.objects.all()) == 0 :
        stats['last_update'] = '--'
    else :
        stats['last_update'] = Study.objects.all().order_by("-update_date")[0].update_date.strftime('%b/%d/%Y')
    context = { 'search_form': search_form, 'stats': stats, 'is_rnaseq': True }
    context.update(authentication_context(request))
    return render(request, 'home/home_rnaseq.html', context)

'''
About View of ArachisPheno
'''
@login_if_required
def about(request):
    return render(request, 'home/about.html', authentication_context(request))

'''
Links View of ArachisPheno
'''
@login_if_required
def links(request):
    return render(request, 'home/links.html', authentication_context(request))

'''
FAQ View of ArachisPheno
'''
@login_if_required
def faq(request):
    return render(request, 'home/faq.html', authentication_context(request))

'''
FAQ Content View of ArachisPheno
'''
@login_if_required
def faqcontent(request):
    return render(request, 'home/faqcontent.html', authentication_context(request))

'''
FAQ Tutorial Content View of ArachisPheno
'''
@login_if_required
def faqtutorial(request):
    return render(request, 'home/tutorials.html', authentication_context(request))

'''
FAQ REST Content View of ArachisPheno
'''
@login_if_required
def faqrest(request):
    return render(request, 'home/faqrest.html', authentication_context(request))

'''
FAQ Cite Content View of ArachisPheno
'''
@login_if_required
def faqcite(request):
    return render(request, 'home/faqcite.html', authentication_context(request))

'''
FAQ Issue Content View of ArachisPheno
'''
@login_if_required
def faqissue(request):
    return render(request, 'home/faqissue.html', authentication_context(request))

'''
Search Result View for Global Search in ArachisPheno
'''
@login_if_required
def SearchResults(request,query=None):
    if query==None:
        phenotypes = Phenotype.objects.published().all()
        studies = Study.objects.published().all()
        accessions = Accession.objects.all()
        ontologies = OntologyTerm.objects.all()
        download_url = "/rest/search"
    else:
        phenotypes = Phenotype.objects.published().filter(Q(name__icontains=query) |
                                              Q(to_term__id__icontains=query) |
                                              Q(to_term__name__icontains=query))
        studies = Study.objects.published().filter(name__icontains=query)
        accessions = Accession.objects.filter(name__icontains=query)
        ontologies = OntologyTerm.objects.filter(name__icontains=query)
        download_url = "/rest/search/" + str(query)

    phenotype_table = PhenotypeTable(phenotypes,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(phenotype_table)

    study_table = StudyTable(studies,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(study_table)

    accession_table = AccessionTable(accessions,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(accession_table)

    ontologies_table = OntologyTermTable(ontologies,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(ontologies_table)

    variable_dict = {}
    variable_dict['query'] = query
    variable_dict['nphenotypes'] = phenotypes.count()
    variable_dict['phenotype_table'] = phenotype_table
    variable_dict['accession_table'] = accession_table
    variable_dict['ontologies_table'] = ontologies_table
    variable_dict['study_table'] = study_table

    variable_dict['nstudies'] = studies.count()
    variable_dict['naccessions'] = accessions.count()
    variable_dict['nontologies'] = ontologies.count()
    variable_dict['download_url'] = download_url

    variable_dict.update(authentication_context(request))
    return render(request,'home/search_results.html',variable_dict)

# RNASeq search
@login_if_required
def SearchResultsRNASeq(request,query=None):
    studies = Study.objects.published().annotate(pheno_count=Count('phenotype')).annotate(rna_count=Count('rnaseq'))
    studies = studies.filter(pheno_count=0).filter(rna_count__gt=0)
    if query==None:
        rnaseqs = RNASeq.objects.all()
        studies = studies.all()
        accessions = Accession.objects.all()
        download_url = "/rest/rnaseq_search"
    else:
        rnaseqs = RNASeq.objects.filter(Q(name__icontains=query) |
                                        Q(growth_conditions__icontains=query))
        studies = studies.filter(name__icontains=query)
        accessions = Accession.objects.filter(name__icontains=query)
        download_url = "/rest/rnaseq_search/" + str(query)

    rnaseq_table = RNASeqTable(rnaseqs,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(rnaseq_table)

    study_table = RNASeqStudyTable(studies,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(study_table)

    accession_table = AccessionTable(accessions,order_by="name")
    RequestConfig(request,paginate={"per_page":10}).configure(accession_table)

    variable_dict = {}
    variable_dict['query'] = query
    variable_dict['nrnaseqs'] = rnaseqs.count()
    variable_dict['rnaseq_table'] = rnaseq_table
    variable_dict['accession_table'] = accession_table
    variable_dict['study_table'] = study_table

    variable_dict['nstudies'] = studies.count()
    variable_dict['naccessions'] = accessions.count()
    variable_dict['download_url'] = download_url

    variable_dict.update(authentication_context(request))
    return render(request,'home/rnaseq_search_results.html',variable_dict)

'''
Logout View of ArachisPheno
'''
def logout_request(request) :
    if not REQUIRE_USER_AUTHENTICATION :
        return redirect(settings.LOGIN_REDIRECT_URL)

    logout(request)
    return render(request, 'home/logout.html', {})

