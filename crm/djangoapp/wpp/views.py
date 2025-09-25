import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Tag, Contact
from .forms import TagForm, ContactForm, ContactImportForm
from accounts.mixins import CompanyRequiredMixin

class DashboardView(CompanyRequiredMixin, TemplateView):
    template_name = 'wpp/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.request.user.company
        
        context.update({
            'total_contatos': Contact.objects.filter(company=company).count(),
            'contatos_ativos': Contact.objects.filter(company=company, ativo=True).count(),
            'total_tags': Tag.objects.filter(company=company).count(),
            'contatos_recentes': Contact.objects.filter(company=company).prefetch_related('tags').order_by('-created_at')[:5],
        })
        return context


# =============================================================================
# TAG VIEWS
# =============================================================================

class TagListView(CompanyRequiredMixin, ListView):
    model = Tag
    template_name = 'wpp/tags/list.html'
    context_object_name = 'tags'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            total_contatos=Count('contatos')
        )
        
        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        
        return queryset.order_by('nome')


class TagCreateView(CompanyRequiredMixin, CreateView):
    model = Tag
    form_class = TagForm
    template_name = 'wpp/tags/form.html'
    success_url = reverse_lazy('wpp:tag_list')
    
    def form_valid(self, form):
        # Definir company ANTES de salvar para evitar erro de validação
        form.instance.company = self.request.user.company
        messages.success(self.request, 'Tag criada com sucesso!')
        return super().form_valid(form)


class TagUpdateView(CompanyRequiredMixin, UpdateView):
    model = Tag
    form_class = TagForm
    template_name = 'wpp/tags/form.html'
    success_url = reverse_lazy('wpp:tag_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Tag atualizada com sucesso!')
        return super().form_valid(form)


class TagDeleteView(CompanyRequiredMixin, DeleteView):
    model = Tag
    template_name = 'wpp/tags/confirm_delete.html'
    success_url = reverse_lazy('wpp:tag_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Tag deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# CONTACT VIEWS
# =============================================================================

class ContactListView(CompanyRequiredMixin, ListView):
    model = Contact
    template_name = 'wpp/contacts/list.html'
    context_object_name = 'contatos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('company').prefetch_related('tags')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) | 
                Q(telefone__icontains=search) |
                Q(email__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)
        
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__id=tag)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.filter(company=self.request.user.company)
        return context


class ContactDetailView(CompanyRequiredMixin, DetailView):
    model = Contact
    template_name = 'wpp/contacts/detail.html'
    context_object_name = 'contato'


class ContactCreateView(CompanyRequiredMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'wpp/contacts/form.html'
    success_url = reverse_lazy('wpp:contact_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        # Definir company ANTES de salvar para evitar erro de validação
        form.instance.company = self.request.user.company
        messages.success(self.request, 'Contato criado com sucesso!')
        return super().form_valid(form)


class ContactUpdateView(CompanyRequiredMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = 'wpp/contacts/form.html'
    success_url = reverse_lazy('wpp:contact_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Contato atualizado com sucesso!')
        return super().form_valid(form)


class ContactDeleteView(CompanyRequiredMixin, DeleteView):
    model = Contact
    template_name = 'wpp/contacts/confirm_delete.html'
    success_url = reverse_lazy('wpp:contact_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Contato deletado com sucesso!')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# IMPORT/EXPORT VIEWS
# =============================================================================

class ContactImportView(CompanyRequiredMixin, View):
    template_name = 'wpp/contacts/import.html'
    
    def get(self, request):
        form = ContactImportForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ContactImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'O arquivo deve ser um CSV.')
                return render(request, self.template_name, {'form': form})
            
            # Processa o arquivo CSV
            try:
                decoded_file = csv_file.read().decode('utf-8')
                csv_data = csv.DictReader(io.StringIO(decoded_file))
                
                created_count = 0
                error_count = 0
                errors = []
                
                for row_num, row in enumerate(csv_data, start=2):
                    try:
                        # Valida campos obrigatórios
                        if not row.get('nome') or not row.get('telefone'):
                            errors.append(f"Linha {row_num}: Nome e telefone são obrigatórios")
                            error_count += 1
                            continue
                        
                        # Verifica se contato já existe
                        telefone = row['telefone'].strip()
                        if Contact.objects.filter(telefone=telefone, company=request.user.company).exists():
                            errors.append(f"Linha {row_num}: Telefone {telefone} já existe")
                            error_count += 1
                            continue
                        
                        # Cria o contato
                        contato = Contact.objects.create(
                            nome=row['nome'].strip(),
                            telefone=telefone,
                            email=row.get('email', '').strip() or None,
                            company=request.user.company,
                            origem='importacao_csv'
                        )
                        
                        # Adiciona tags se existirem
                        tags_str = row.get('tags', '').strip()
                        if tags_str:
                            tag_names = [tag.strip() for tag in tags_str.split(',')]
                            for tag_name in tag_names:
                                if tag_name:
                                    contato.adicionar_tag(tag_name)
                        
                        created_count += 1
                        
                    except Exception as e:
                        errors.append(f"Linha {row_num}: {str(e)}")
                        error_count += 1
                
                # Mensagens de resultado
                if created_count > 0:
                    messages.success(request, f'{created_count} contatos importados com sucesso!')
                
                if error_count > 0:
                    error_msg = f'{error_count} erros encontrados:\n' + '\n'.join(errors[:10])
                    if len(errors) > 10:
                        error_msg += f'\n... e mais {len(errors) - 10} erros'
                    messages.error(request, error_msg)
                
                return redirect('wpp:contact_list')
                
            except Exception as e:
                messages.error(request, f'Erro ao processar arquivo: {str(e)}')
        
        return render(request, self.template_name, {'form': form})


class ContactExportView(CompanyRequiredMixin, View):
    def get(self, request):
        # Cria o HttpResponse com CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contatos.csv"'
        
        writer = csv.writer(response)
        
        # Cabeçalho
        writer.writerow(['nome', 'telefone', 'email', 'tags', 'ativo', 'criado_em'])
        
        # Dados
        contatos = Contact.objects.filter(company=request.user.company).prefetch_related('tags')
        for contato in contatos:
            tags_str = ', '.join(contato.tags_nomes)
            writer.writerow([
                contato.nome,
                contato.telefone,
                contato.email or '',
                tags_str,
                'Sim' if contato.ativo else 'Não',
                contato.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        return response


# =============================================================================
# AJAX VIEWS
# =============================================================================

class AjaxContactsListView(CompanyRequiredMixin, View):
    def get(self, request):
        contatos = Contact.objects.filter(
            company=request.user.company
        ).prefetch_related('tags').order_by('-created_at')[:10]
        
        total_contatos = Contact.objects.filter(company=request.user.company).count()
        
        html = render_to_string('wpp/ajax/contacts_list.html', {
            'contatos': contatos,
            'total_contatos': total_contatos
        }, request=request)
        
        return HttpResponse(html)


class AjaxTagsListView(CompanyRequiredMixin, View):
    def get(self, request):
        tags = Tag.objects.filter(
            company=request.user.company
        ).annotate(total_contatos=Count('contatos')).order_by('nome')[:10]
        
        total_tags = Tag.objects.filter(company=request.user.company).count()
        
        html = render_to_string('wpp/ajax/tags_list.html', {
            'tags': tags,
            'total_tags': total_tags
        }, request=request)
        
        return HttpResponse(html)


class AjaxContactFormView(CompanyRequiredMixin, View):
    def get(self, request, pk=None):
        contact = None
        if pk:
            contact = get_object_or_404(Contact, pk=pk, company=request.user.company)
            form = ContactForm(instance=contact, company=request.user.company)
        else:
            form = ContactForm(company=request.user.company)
        
        html = render_to_string('wpp/ajax/contact_form.html', {
            'form': form,
            'contact': contact
        }, request=request)
        
        return HttpResponse(html)


@method_decorator(csrf_exempt, name='dispatch')
class AjaxContactSaveView(CompanyRequiredMixin, View):
    def post(self, request):
        contact_id = request.POST.get('contact_id')
        contact = None
        
        if contact_id:
            contact = get_object_or_404(Contact, pk=contact_id, company=request.user.company)
            form = ContactForm(request.POST, instance=contact, company=request.user.company)
        else:
            form = ContactForm(request.POST, company=request.user.company)
        
        if form.is_valid():
            contact = form.save(commit=False)
            # IMPORTANTE: Definir company ANTES de qualquer save() para evitar erro de validação
            if not contact.company_id:
                contact.company = request.user.company
            contact.save()
            form.save_m2m()
            
            return JsonResponse({
                'success': True,
                'message': 'Contato salvo com sucesso!'
            })
        else:
            html = render_to_string('wpp/ajax/contact_form.html', {
                'form': form,
                'contact': contact
            }, request=request)
            
            return JsonResponse({
                'success': False,
                'form_html': html
            })


class AjaxTagFormView(CompanyRequiredMixin, View):
    def get(self, request, pk=None):
        tag = None
        if pk:
            tag = get_object_or_404(Tag, pk=pk, company=request.user.company)
            form = TagForm(instance=tag)
        else:
            form = TagForm()
        
        html = render_to_string('wpp/ajax/tag_form.html', {
            'form': form,
            'tag': tag
        }, request=request)
        
        return HttpResponse(html)


@method_decorator(csrf_exempt, name='dispatch')
class AjaxTagSaveView(CompanyRequiredMixin, View):
    def post(self, request):
        tag_id = request.POST.get('tag_id')
        tag = None
        
        if tag_id:
            tag = get_object_or_404(Tag, pk=tag_id, company=request.user.company)
            form = TagForm(request.POST, instance=tag)
        else:
            form = TagForm(request.POST)
        
        if form.is_valid():
            tag = form.save(commit=False)
            # IMPORTANTE: Definir company ANTES de qualquer save() para evitar erro de validação
            if not tag.company_id:
                tag.company = request.user.company
            tag.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Tag salva com sucesso!'
            })
        else:
            html = render_to_string('wpp/ajax/tag_form.html', {
                'form': form,
                'tag': tag
            }, request=request)
            
            return JsonResponse({
                'success': False,
                'form_html': html
            })


class AjaxImportFormView(CompanyRequiredMixin, View):
    def get(self, request):
        form = ContactImportForm()
        
        html = render_to_string('wpp/ajax/import_form.html', {
            'form': form
        }, request=request)
        
        return HttpResponse(html)


@method_decorator(csrf_exempt, name='dispatch')
class AjaxImportContactsView(CompanyRequiredMixin, View):
    def post(self, request):
        form = ContactImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                html = render_to_string('wpp/ajax/import_form.html', {
                    'form': form,
                    'error': 'O arquivo deve ser um CSV.'
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'form_html': html
                })
            
            try:
                decoded_file = csv_file.read().decode('utf-8')
                csv_data = csv.DictReader(io.StringIO(decoded_file))
                
                created_count = 0
                error_count = 0
                
                for row in csv_data:
                    try:
                        if not row.get('nome') or not row.get('telefone'):
                            error_count += 1
                            continue
                        
                        telefone = row['telefone'].strip()
                        if Contact.objects.filter(telefone=telefone, company=request.user.company).exists():
                            error_count += 1
                            continue
                        
                        contato = Contact.objects.create(
                            nome=row['nome'].strip(),
                            telefone=telefone,
                            email=row.get('email', '').strip() or None,
                            company=request.user.company,
                            origem='importacao_csv'
                        )
                        
                        tags_str = row.get('tags', '').strip()
                        if tags_str:
                            tag_names = [tag.strip() for tag in tags_str.split(',')]
                            for tag_name in tag_names:
                                if tag_name:
                                    contato.adicionar_tag(tag_name)
                        
                        created_count += 1
                        
                    except Exception:
                        error_count += 1
                
                return JsonResponse({
                    'success': True,
                    'imported': created_count,
                    'errors': error_count
                })
                
            except Exception as e:
                html = render_to_string('wpp/ajax/import_form.html', {
                    'form': form,
                    'error': f'Erro ao processar arquivo: {str(e)}'
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'form_html': html
                })
        else:
            html = render_to_string('wpp/ajax/import_form.html', {
                'form': form
            }, request=request)
            
            return JsonResponse({
                'success': False,
                'form_html': html
            })


@method_decorator(csrf_exempt, name='dispatch')
class AjaxContactDeleteView(CompanyRequiredMixin, View):
    def post(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk, company=request.user.company)
        contact.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Contato excluído com sucesso!'
        })


@method_decorator(csrf_exempt, name='dispatch')
class AjaxTagDeleteView(CompanyRequiredMixin, View):
    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk, company=request.user.company)
        tag.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Tag excluída com sucesso!'
        })


class AjaxStatsView(CompanyRequiredMixin, View):
    def get(self, request):
        company = request.user.company
        
        stats = {
            'total_contatos': Contact.objects.filter(company=company).count(),
            'contatos_ativos': Contact.objects.filter(company=company, ativo=True).count(),
            'total_tags': Tag.objects.filter(company=company).count(),
        }
        
        return JsonResponse(stats)