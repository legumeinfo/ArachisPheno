from django.http import HttpResponse
from django.db.models import Q
from django.db.models import Count
from django.http import FileResponse
from django.core.mail import EmailMessage

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny

from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser, MultiPartParser, FormParser
from rest_framework.views import APIView

from phenotypedb.models import Phenotype, Study, PhenotypeValue, Accession, Submission, OntologyTerm, OntologySource, RNASeq
from phenotypedb.serializers import PhenotypeListSerializer, StudyListSerializer, OntologyTermListSerializer
from phenotypedb.serializers import PhenotypeValueSerializer, ReducedPhenotypeValueSerializer
from phenotypedb.serializers import AccessionListSerializer, SubmissionDetailSerializer, AccessionPhenotypesSerializer

from phenotypedb.forms import UploadFileForm
from phenotypedb.renderer import PhenotypeListRenderer, StudyListRenderer, PhenotypeValueRenderer, PhenotypeMatrixRenderer, IsaTabFileRenderer, AccessionListRenderer, ZipFileRenderer, TransformationRenderer
from phenotypedb.renderer import PLINKRenderer, PLINKMatrixRenderer
from phenotypedb.parsers import AccessionTextParser
from utils.isa_tab import export_isatab
from utils import calculate_phenotype_transformations
from django.views.decorators.csrf import csrf_exempt
import scipy as sp
import scipy.stats as stats
from django.conf import settings

from home.decorators import login_if_required

import re,os,array
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

DOI_REGEX_STUDY = r"%s\/study:[\d]+" % settings.DATACITE_PREFIX
DOI_REGEX_PHENOTYPE = r"%s\/phenotype:[\d]+" % settings.DATACITE_PREFIX

DOI_PATTERN_STUDY = re.compile(DOI_REGEX_STUDY)
DOI_PATTERN_PHENOTYPE = re.compile(DOI_REGEX_PHENOTYPE)
GENEID_REGEX = r"AT[1-5|M|C]G[\d]*(\.[\d]){0,1}"
GENEID_PATTERN =  re.compile(GENEID_REGEX)

'''
Search Endpoint
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@login_if_required
def search(request,query_term=None,format=None):
    """
    Search for a phenotype or study
    ---
    parameters:
        - name: query_term
          description: the search term
          required: true
          type: string
          paramType: path

    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    if request.method == "GET":
        if query_term==None:
            studies = Study.objects.published().all()
            phenotypes = Phenotype.objects.published().all()
            accessions = Accession.objects.all()
            ontologies = OntologyTerm.objects.all()
        else:
            studies = Study.objects.published().filter(name__icontains=query_term)
            phenotypes = Phenotype.objects.published().filter(Q(name__icontains=query_term) |
                                                  Q(to_term__id__icontains=query_term) |
                                                  Q(to_term__name__icontains=query_term))
            accessions = Accession.objects.filter(Q(id__icontains=query_term) | Q(name__icontains=query_term))
            ontologies = OntologyTerm.objects.filter(name__icontains=query_term)

        study_serializer = StudyListSerializer(studies,many=True)
        phenotype_serializer = PhenotypeListSerializer(phenotypes,many=True)
        accession_serializer = AccessionListSerializer(accessions,many=True)
        ontology_serializer = OntologyTermListSerializer(ontologies,many=True)
        return Response({'phenotype_search_results':phenotype_serializer.data,
                         'study_search_results':study_serializer.data,
                         'accession_search_results':accession_serializer.data,
                         'ontology_search_results':ontology_serializer.data})

'''
List all phenotypes
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeListRenderer,JSONRenderer))
@login_if_required
def phenotype_list(request,format=None):
    """
    List all available phenotypes
    ---
    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    phenotypes = Phenotype.objects.annotate(num_values=Count('phenotypevalue')).published()
    if request.method == "GET":
        serializer = PhenotypeListSerializer(phenotypes,many=True)
        return Response(serializer.data)


'''
List all similar phenotypes
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeListRenderer,JSONRenderer))
@login_if_required
def phenotype_similar_list(request,q,format=None):
    """
    List all available phenotypes matching phenotype q's trait ontology
    ---
    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_PHENOTYPE,q)
    try:
        id = doi if doi else int(q)
        phenotype = Phenotype.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)
    to_term = phenotype.to_term.id
    phenotypes = Phenotype.objects.published().filter(to_term__id=to_term)

    if request.method == "GET":
        serializer = PhenotypeListSerializer(phenotypes,many=True)
        return Response(serializer.data)


'''
Detail information about phenotype
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeListRenderer,JSONRenderer))
@login_if_required
def phenotype_detail(request,q,format=None):
    """
    Detailed information about the phenotype
    ---
    parameters:
        - name: q
          description: the id or doi of the phenotype
          required: true
          type: string
          paramType: path

    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json

    """
    doi = _is_doi(DOI_PATTERN_PHENOTYPE,q)

    try:
        id = doi if doi else int(q)
        phenotype = Phenotype.objects.published().annotate(num_values=Count('phenotypevalue')).get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = PhenotypeListSerializer(phenotype,many=False)
        return Response(serializer.data)


'''
Get all phenotype values
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeValueRenderer,JSONRenderer,PLINKRenderer,))
@login_if_required
def phenotype_value(request,q,format=None):
    """
    List of the phenotype values
    ---
    parameters:
        - name: q
          description: the id or doi of the phenotype
          required: true
          type: string
          paramType: path

    serializer: PhenotypeValueSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_PHENOTYPE, q)
    try:
        id = doi if doi else int(q)
        phenotype = Phenotype.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        pheno_acc_infos = phenotype.phenotypevalue_set.prefetch_related('obs_unit__accession')
        value_serializer = PhenotypeValueSerializer(pheno_acc_infos,many=True)
        return Response(value_serializer.data)

'''
Get all rnaseq values
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeValueRenderer,JSONRenderer,PLINKRenderer,))
@login_if_required
def rnaseq_value_by_gene_id(request,study_id,gene_id,format=None):
    """
    List of the rnaseq values
    ---
    parameters:
        - name: study_id
          description: the id of the study
          required: true
          type: int
          paramType: path
        - name: gene_id
          description: the gene_id for the rnaseq values
          required: true
          type: string
          paramType: path

    serializer: PhenotypeValueSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    study_id = int(study_id)
    gene_id = _is_geneid(gene_id)
    try:
        rnaseq = RNASeq.objects.filter(study__id=study_id,name=gene_id).first()
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        pheno_acc_infos = rnaseq.rnaseqvalue_set.prefetch_related('obs_unit__accession')
        value_serializer = PhenotypeValueSerializer(pheno_acc_infos,many=True)
        return Response(value_serializer.data)

'''
Get all rnaseq values
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeValueRenderer,JSONRenderer,PLINKRenderer,))
@login_if_required
def rnaseq_value(request,q,format=None):
    """
    List of the rnaseq values
    ---
    parameters:
        - name: q
          description: the id or doi of the rnaseq
          required: true
          type: string
          paramType: path

    serializer: PhenotypeValueSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_PHENOTYPE, q)
    try:
        id = doi if doi else int(q)
        rnaseq = RNASeq.objects.get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        pheno_acc_infos = rnaseq.rnaseqvalue_set.prefetch_related('obs_unit__accession')
        value_serializer = PhenotypeValueSerializer(pheno_acc_infos,many=True)
        return Response(value_serializer.data)

'''
List all studies
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((StudyListRenderer,JSONRenderer))
@login_if_required
def study_list(request,format=None):
    """
    List all available studies
    ---

    serializer: StudyListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    studies = Study.objects.published().all()
    if request.method == "GET":
        serializer = StudyListSerializer(studies,many=True)
        return Response(serializer.data)


'''
Get detailed information about study
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((StudyListRenderer,JSONRenderer))
@login_if_required
def study_detail(request,q,format=None):
    """
    Retrieve detailed information about the study
    ---

    serializer: StudyListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_STUDY, q)

    try:
        id = doi if doi else int(q)
        study = Study.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = StudyListSerializer(study,many=False)
        return Response(serializer.data)


'''
List all phenotypes for study id/doi
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeListRenderer,JSONRenderer,))
@login_if_required
def study_all_pheno(request,q=None,format=None):
    """
    List all phenotypes for a study
    ---

    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_STUDY, q)
    try:
        id = doi if doi else int(q)
        study = Study.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        serializer = PhenotypeListSerializer(study.phenotype_set.all().annotate(num_values=Count('phenotypevalue')),many=True)
        return Response(serializer.data)

'''
List phenotype value matrix for entire study
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeMatrixRenderer,PLINKMatrixRenderer,JSONRenderer))
@login_if_required
def study_phenotype_value_matrix(request,q,format=None):
    """
    Phenotype value matrix for entire study
    ---
    parameters:
        - name: q
          description: the primary id or doi of the study
          required: true
          type: string
          paramType: path

    produces:
        - text/csv
        - application/json
        - application/plink
    """
    doi = _is_doi(DOI_PATTERN_STUDY, q)
    try:
        id = doi if doi else int(q)
        study = Study.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        df,df_pivot = study.get_matrix_and_accession_map()
        data = _convert_dataframe_to_list(df,df_pivot)
        return Response(data)

@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((TransformationRenderer,JSONRenderer))
@login_if_required
def transformations(request,q,transformation=None, format=None):
    """
    Transformation of phenotypes
    ---
    parameters:
        - name: q
          description: the primary id or doi of the phenotype
          required: true
          type: string
          paramType: path
        - name: transformation
          description: the transformation to be calculates (if omitted, all transformations are returned)
          required: false
          type: string
          paramType: path

    produces:
        - text/csv
        - application/json
    """
    doi = _is_doi(DOI_PATTERN_PHENOTYPE, q)
    try:
        id = doi if doi else int(q)
        phenotype = Phenotype.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    if request.method == "GET":
        data = calculate_phenotype_transformations(phenotype, transformation)
        return Response(data)


'''
Correlation Matrix for selected phenotypes
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((JSONRenderer,))
@login_if_required
def phenotype_correlations(request,q=None):
    """
    Return data for phenotype-phenotype correlations and between phenotype accession overlap
    ---

    produces:
        - application/json
    """
    #id string to list
    pids = map(int,q.split(","))
    pheno_dict = {}
    for i,pid in enumerate(pids):
        try:
            phenotype = Phenotype.objects.published().get(pk=pid)
        except:
            return Response({'message':'FAILED','not_found':pid})
        pheno_acc_infos = phenotype.phenotypevalue_set.prefetch_related('obs_unit__accession')
        values = sp.array(pheno_acc_infos.values_list('value',flat=True))
        samples = sp.array(pheno_acc_infos.values_list('obs_unit__accession__id',flat=True))
        name = str(phenotype.name.replace("<i>","").replace("</i>","") + " (" + str(phenotype.study.name) + ")")
        pheno_dict[str(phenotype.name) + "_" + str(phenotype.study.name) + "_" + str(i)] = {'samples':samples,
                                                                                            'y':values,
                                                                                            'name':name,
                                                                                            'id':str(phenotype.id)}
                                                                                            #str(phenotype.name) + "_" + str(phenotype.study.name) + "_" + str(i)}
    #compute correlation matrix
    corr_mat = sp.ones((len(pheno_dict),len(pheno_dict))) * sp.nan
    spear_mat = sp.ones((len(pheno_dict),len(pheno_dict))) * sp.nan
    pheno_keys = pheno_dict.keys()
    axes_data = []
    scatter_data = []
    sample_data = []
    slabels = {}
    for i,pheno1 in enumerate(pheno_keys):
        axes_data.append({"label":pheno_dict[pheno1]['name'],
                          "index":str(i),
                          "pheno_id":str(pheno_dict[pheno1]['id'])})
        samples1 = pheno_dict[pheno1]['samples']
        y1 = pheno_dict[pheno1]['y']
        #store scatter data
        scatter_data.append({"label":pheno_dict[pheno1]['name'],
                             "pheno_id":str(pheno_dict[pheno1]['id']),
                             "samples": samples1.tolist(),
                             "values":y1.tolist()})

        for j,pheno2 in enumerate(pheno_keys):
            samples2 = pheno_dict[pheno2]['samples']
            y2 = pheno_dict[pheno2]['y']
            #match accessions
            ind = (sp.reshape(samples1,(samples1.shape[0],1))==samples2).nonzero()
            y_tmp = y1[ind[0]]
            y2 = y2[ind[1]]
            if y1.shape[0]>0 and y2.shape[0]>0:
                corr_mat[i][j] = stats.pearsonr(y_tmp.flatten(),y2.flatten())[0]
                spear_mat[i][j] = stats.spearmanr(y_tmp.flatten(),y2.flatten())[0]
            #compute sample intersections
            if pheno1==pheno2:
                continue
            if pheno1 + "_" + pheno2 in slabels:
                continue
            if pheno2 + "_" + pheno1 in slabels:
                continue
            slabels[pheno1 + "_" + pheno2] = True
            A = samples1.shape[0]
            B = samples2.shape[0]
            C = sp.intersect1d(samples1,samples2).shape[0]
            sample_data.append({"labelA":pheno_dict[pheno1]['name'],
                                "labelA_id":pheno_dict[pheno1]['id'],
                                "labelB":pheno_dict[pheno2]['name'],
                                "labelB_id":pheno_dict[pheno2]['id'],
                                "A":A, "B":B, "C":C})
    data = {}
    data['axes_data'] = axes_data
    data['scatter_data'] = scatter_data
    data['sample_data'] = sample_data
    data['corr_mat'] = str(corr_mat.tolist()).replace("nan","NaN")
    data['spear_mat'] = str(spear_mat.tolist()).replace("nan","NaN")

    if request.method == "GET":
        return Response(data)


'''
Returns ISA-TAB archive
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((IsaTabFileRenderer,JSONRenderer))
@login_if_required
def study_isatab(request,q,format=None):
    """
    Generate ISA-TAB archive for a study
    ---
    parameters:
        - name: q
          description: the primary id or doi of the study
          required: true
          type: string
          paramType: path

    produces:
        - application/zip
    """
    doi = _is_doi(DOI_PATTERN_STUDY, q)
    try:
        id = doi if doi else int(q)
        study = Study.objects.published().get(pk=id)
    except:
        return HttpResponse(status=404)

    isa_tab_file = export_isatab(study)
    zip_file = open(isa_tab_file, 'rb')
    response = FileResponse(zip_file,content_type='application/zip')
    #response = HttpResponse(FileWrapper(zip_file), content_type='application/zip',content_transfer_encoding='binary')
    response.setdefault('Content-Transfer-Encoding','binary')
    response['Content-Disposition'] = 'attachment; filename="isatab_study_%s.zip"' % study.id
    os.unlink(isa_tab_file)
    return response

'''
List all accessions
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((AccessionListRenderer,JSONRenderer))
@login_if_required
def accession_list(request,format=None):
    """
    List all accessions
    ---

    serializer: AccessionListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    if request.method == "GET":
        if 'genotypes' in request.GET:
            genotype_ids = map(int, request.GET['genotypes'].split(','))
            accessions = Accession.objects.annotate(count_phenotypes=Count('observationunit__phenotypevalue__phenotype', distinct=True)).select_related('species').prefetch_related('genotype_set').filter(genotype__pk__in = genotype_ids)
        else:
            accessions = Accession.objects.annotate(count_phenotypes=Count('observationunit__phenotypevalue__phenotype', distinct=True)).select_related('species').prefetch_related('genotype_set').all()
        serializer = AccessionListSerializer(accessions,many=True)
        return Response(serializer.data)

'''
Get detailed information about accession
'''
@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((AccessionListRenderer,JSONRenderer))
@login_if_required
def accession_detail(request,pk,format=None):
    """
    Retrieve detailed information about the accession
    ---

    serializer: AccessionListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """

    accession = Accession.objects.annotate(count_phenotypes=Count('observationunit__phenotypevalue__phenotype', distinct=True)).get(pk=pk)

    if request.method == "GET":
        serializer = AccessionListSerializer(accession,many=False)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((PhenotypeListRenderer,JSONRenderer,))
@login_if_required
def accession_phenotypes(request,pk,format=None):
    """
    List all phenotypes for an accession
    ---

    serializer: PhenotypeListSerializer
    omit_serializer: false

    produces:
        - text/csv
        - application/json
    """
    phenotypes = Phenotype.objects.published().filter(phenotypevalue__obs_unit__accession_id=pk).annotate(num_values=Count('phenotypevalue'))

    if request.method == "GET":
        serializer = PhenotypeListSerializer(phenotypes,many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
@parser_classes((JSONParser, AccessionTextParser))
@login_if_required
def accessions_phenotypes(request,format=None):
    """
    Retrieve all phenotypes for a list of accessions
    ---

    serializer: AccessionPhenotypesSerializer
    omit_serializer: false

    consumes:
        - text/plain

    produces:
        - application/json
    """
    acc_phenotype_list = {}
    for id in set(request.data):
        acc_phenotype_list[id] = Phenotype.objects.published().filter(phenotypevalue__obs_unit__accession_id=id).annotate(num_values=Count('phenotypevalue'))
    if request.method == "POST":
        serializer = AccessionPhenotypesSerializer(acc_phenotype_list)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
@renderer_classes((JSONRenderer,))
@login_if_required
def ontology_tree_data(request,acronym=None,term_id=None,format=None):
    """
    Retrieve ontology tree structure
    ---
    produces:
        - application/json
    """
    if term_id is not None:
        term = OntologyTerm.objects.get(pk=term_id)
        data = [{'text':t.name,'id':t.id, 'children': True if t.children.count() > 0 else False} for t in term.children.all()]
    else:
        source = OntologySource.objects.get(acronym=acronym)
        roots = source.ontologyterm_set.filter(parents=None)
        data = [{'text':term.name,'id':term.id,'children':True if term.children.count() > 0 else False} for term in roots]
    return Response(data)



@api_view(['POST'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
@parser_classes((FormParser, MultiPartParser))
@login_if_required
def submit_study(request,format=None):
    """
    Submit a study
    ---

    serializer: SubmissionDetailSerializer
    omit_serializer: false

    produces:
        - application/json
    """
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                submission = form.save()
                email = EmailMessage(
                    submission.get_email_subject(),
                    submission.get_email_text(),
                    settings.EMAIL_ADDRESS,
                    [submission.email],
                    [settings.EMAIL_ADDRESS],
                    reply_to=[settings.EMAIL_ADDRESS]
                )
                email.send(True)
                serializer = SubmissionDetailSerializer(submission,many=False,context={'request': request})

                return Response(serializer.data, status.HTTP_201_CREATED)
            except Accession.DoesNotExist as err:
                return Response('Unknown accession with ID: %s' % err.args[-1],status.HTTP_400_BAD_REQUEST)
            except Exception as err:
                return Response(str(err),status.HTTP_400_BAD_REQUEST)
        else:
            return Response('Some fields are missing',status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
@login_if_required
def submission_infos(request,pk,format=None):
    """
    Retrieve detailed information about the submission
    ---

    serializer: SubmissionDetailSerializer
    omit_serializer: false

    produces:
        - application/json
    """
    if request.method == "GET":
        try:
            submission = Submission.objects.get(pk=pk)
            serializer = SubmissionDetailSerializer(submission,many=False,context={'request': request})
            return Response(serializer.data)
        except Exception as err:
            return HttpResponse(str(err),status=404)

@csrf_exempt
@api_view(['DELETE'])
@permission_classes((AllowAny,))
@renderer_classes((JSONRenderer,))
@login_if_required
def delete_submission(request,pk,format=None):
    """
    Deletes a submission
    ---
    omit_serializer: false

    produces:
        - application/json
    """
    if request.method == "DELETE":
        try:

            submission = Submission.objects.get(pk=pk)
            if submission.status != 2:
                submission.study.delete()
                return Response(status.HTTP_204_NO_CONTENT)
            else:
                return Response(status.HTTP_403_FORBIDDEN)
        except Exception as err:
            return HttpResponse(str(err),status=404)




def _convert_dataframe_to_list(df, df_pivot):
    df_pivot = df_pivot.fillna('')
    data = []
    headers = df_pivot.columns.tolist()
    for obs_unit_id,row in df_pivot.iterrows():
        info = df.ix[obs_unit_id]
        accession_id = info.accession_id
        accession_name = info.accession_name
        csv_row = {'obs_unit_id':obs_unit_id,'accession_id':accession_id,'accession_name':accession_name}
        for i,value in enumerate(row.values):
            csv_row[headers[i]] = value
        data.append(csv_row)
    return data



def _is_doi(pattern, term):
    doi = pattern.match(term)
    if doi:
        # can't use REGEX capture groups because "("" causes problems in Swagger
        return int(term.split(":")[1])
    return None

def _is_geneid(term):
    gene_id = GENEID_PATTERN.match(term)
    if gene_id:
        # can't use REGEX capture groups because "("" causes problems in Swagger
        return gene_id.group()
    return None

def generate_database_dump():
    """
    Generate an archive of the full database
    (python manage.py generate_database_dump)
    """
    # destination for archive
    dest_dir = settings.STATICFILES_DIRS[0]
    database_filename = "database"
    output_filename = os.path.join(dest_dir, '%s.zip' % database_filename)

    # create temporary folder
    folder = tempfile.mkdtemp()

    # Get list of study ids
    studies = Study.objects.published().filter(rnaseq__isnull=True).all()
    # Create subfolders
    for study in studies:
        os.makedirs(os.path.join(folder, str(study.id)))

    # create the isatab files
    _create_value_files(studies, folder, fmt='csv')
    _create_value_files(studies, folder, fmt='plink')
    _create_study_list_file(studies, folder)
    _create_phenotypes_files(studies, folder)

    # zip it
    output_filename = shutil.make_archive(database_filename, "zip", folder)
    shutil.move(output_filename, os.path.join(dest_dir, os.path.basename(output_filename)))

    # remove temporary folder
    shutil.rmtree(folder)
    return output_filename


def _create_value_files(studies, folder, fmt):
    if fmt == 'csv':
        renderer = PhenotypeMatrixRenderer()
    elif fmt == 'plink':
        renderer = PLINKMatrixRenderer()
    else:
        raise Warning('The format must be csv or plink.')

    for study in studies:
        logger.info("Creating value files for %s" % study)
        df,df_pivot = study.get_matrix_and_accession_map()
        data = _convert_dataframe_to_list(df,df_pivot)
        content = renderer.render(data)
        study_filename = os.path.join(folder,str(study.id),'study_%s_values.%s' % (study.id, fmt))
        with open(study_filename,'w') as f:
            f.write(content)
    pass

def _create_phenotypes_files(studies, folder):
    renderer = PhenotypeListRenderer()
    for study in studies:
        serializer = PhenotypeListSerializer(study.phenotype_set.all(),many=True)
        content = renderer.render(serializer.data)
        study_filename = os.path.join(folder,str(study.id),'study_%s_phenotypes.csv' % study.id)
        with open(study_filename,'w') as f:
            f.write(content)
    pass

def _create_study_list_file(studies, folder):
    renderer = StudyListRenderer()
    serializer = StudyListSerializer(studies,many=True)
    content = renderer.render(serializer.data)
    study_list_filename = os.path.join(folder,'study_list.csv')
    with open(study_list_filename,'w') as f:
        f.write(content)
    pass
