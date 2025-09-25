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
from django.utils import timezone
from .models import Tag, Contact, Campaign, Message, MessageLog
from .forms import TagForm, ContactForm, ContactImportForm, CampaignForm, MessageForm
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
            'total_campanhas': Campaign.objects.filter(company=company).count(),
            'total_mensagens': Message.objects.filter(company=company).count(),
            'contatos_recentes': Contact.objects.filter(company=company).prefetch_related('tags').order_by('-created_at')[:5],
            'campanhas_recentes': Campaign.objects.filter(company=company).order_by('-created_at')[:5],
            'mensagens_recentes': Message.objects.filter(company=company).select_related('campanha').order_by('-created_at')[:5],
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
            'total_campanhas': Campaign.objects.filter(company=company).count(),
            'total_mensagens': Message.objects.filter(company=company).count(),
        }
        
        return JsonResponse(stats)


class AjaxCampaignPreviewView(CompanyRequiredMixin, View):
    """View para buscar texto da campanha via AJAX para prévia"""
    def get(self, request):
        campanha_id = request.GET.get('campanha_id')
        
        if not campanha_id:
            return JsonResponse({'success': False, 'message': 'ID da campanha não fornecido'})
        
        try:
            campanha = Campaign.objects.get(
                pk=campanha_id,
                company=request.user.company
            )
            
            # Processa texto com exemplo de contato
            texto_processado = campanha.texto.replace('{{nome}}', 'João Silva')
            
            return JsonResponse({
                'success': True,
                'texto': texto_processado,
                'nome_campanha': campanha.nome
            })
            
        except Campaign.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Campanha não encontrada'
            })


# =============================================================================
# CAMPAIGN VIEWS
# =============================================================================

class CampaignListView(CompanyRequiredMixin, ListView):
    model = Campaign
    template_name = 'wpp/campaigns/list.html'
    context_object_name = 'campanhas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            total_envios=Count('envios')
        )
        
        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        
        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'ativo':
            queryset = queryset.filter(ativo=True)
        elif status == 'inativo':
            queryset = queryset.filter(ativo=False)
        
        return queryset.order_by('-created_at')


class CampaignDetailView(CompanyRequiredMixin, DetailView):
    model = Campaign
    template_name = 'wpp/campaigns/detail.html'
    context_object_name = 'campanha'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campanha = self.get_object()
        
        # Pega alguns contatos para prévia
        contatos_exemplo = Contact.objects.filter(
            company=self.request.user.company, 
            ativo=True
        )[:3]
        
        context.update({
            'contatos_exemplo': contatos_exemplo,
            'total_envios': campanha.envios.count(),
            'envios_recentes': campanha.envios.order_by('-created_at')[:5],
        })
        return context


class CampaignCreateView(CompanyRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'wpp/campaigns/form.html'
    success_url = reverse_lazy('wpp:campaign_list')
    
    def form_valid(self, form):
        form.instance.company = self.request.user.company
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Campanha criada com sucesso!')
        return super().form_valid(form)


class CampaignUpdateView(CompanyRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'wpp/campaigns/form.html'
    success_url = reverse_lazy('wpp:campaign_list')
    
    def form_valid(self, form):
        # Atualiza o updated_at para registrar a alteração
        form.instance.updated_at = timezone.now()
        messages.success(self.request, 'Campanha atualizada com sucesso!')
        return super().form_valid(form)


class CampaignDeleteView(CompanyRequiredMixin, DeleteView):
    model = Campaign
    template_name = 'wpp/campaigns/confirm_delete.html'
    success_url = reverse_lazy('wpp:campaign_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Campanha deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# MESSAGE VIEWS
# =============================================================================

class MessageListView(CompanyRequiredMixin, ListView):
    model = Message
    template_name = 'wpp/messages/list.html'
    context_object_name = 'mensagens'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('campanha')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) | 
                Q(campanha__nome__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        campanha = self.request.GET.get('campanha')
        if campanha:
            queryset = queryset.filter(campanha__id=campanha)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campanhas'] = Campaign.objects.filter(
            company=self.request.user.company, 
            ativo=True
        )
        return context


class MessageDetailView(CompanyRequiredMixin, DetailView):
    model = Message
    template_name = 'wpp/messages/detail.html'
    context_object_name = 'mensagem'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mensagem = self.get_object()
        
        # Logs de envio
        context['logs'] = mensagem.logs.select_related('contato').order_by('-created_at')[:50]
        
        return context


class MessageCreateView(CompanyRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'wpp/messages/form.html'
    success_url = reverse_lazy('wpp:message_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        form.instance.company = self.request.user.company
        form.instance.created_by = self.request.user
        
        # Salva a mensagem primeiro
        response = super().form_valid(form)
        
        # Atualiza o total de contatos
        self.object.total_contatos = self.object.contatos.count()
        self.object.save(update_fields=['total_contatos'])
        
        messages.success(self.request, 'Mensagem criada com sucesso!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona contatos para seleção
        context['contatos_disponiveis'] = Contact.objects.filter(
            company=self.request.user.company,
            ativo=True
        ).order_by('nome')
        
        return context


class MessageUpdateView(CompanyRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'wpp/messages/form.html'
    success_url = reverse_lazy('wpp:message_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs
    
    def form_valid(self, form):
        # Só permite editar se não foi enviada
        if self.object.status in ['enviando', 'enviada']:
            messages.error(self.request, 'Não é possível editar mensagem já enviada.')
            return redirect('wpp:message_detail', pk=self.object.pk)
        
        # Atualiza o total de contatos
        response = super().form_valid(form)
        self.object.total_contatos = self.object.contatos.count()
        
        # Atualiza o updated_at para registrar a alteração
        self.object.updated_at = timezone.now()
        self.object.save(update_fields=['total_contatos', 'updated_at'])
        
        messages.success(self.request, 'Mensagem atualizada com sucesso!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adiciona contatos para seleção
        context['contatos_disponiveis'] = Contact.objects.filter(
            company=self.request.user.company,
            ativo=True
        ).order_by('nome')
        
        return context


class MessageDeleteView(CompanyRequiredMixin, DeleteView):
    model = Message
    template_name = 'wpp/messages/confirm_delete.html'
    success_url = reverse_lazy('wpp:message_list')
    
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        
        # Não permite deletar se já foi enviada
        if obj.status in ['enviando', 'enviada']:
            messages.error(request, 'Não é possível deletar mensagem já enviada.')
            return redirect('wpp:message_detail', pk=obj.pk)
        
        messages.success(self.request, 'Mensagem deletada com sucesso!')
        return super().delete(request, *args, **kwargs)


class MessageSendView(CompanyRequiredMixin, View):
    """
    View para enviar mensagens
    Futuramente aqui será integrada a API da Evolution
    """
    template_name = 'wpp/messages/send_confirm.html'
    
    def get(self, request, pk):
        message = get_object_or_404(Message, pk=pk, company=request.user.company)
        
        if not message.pode_enviar():
            messages.error(request, 'Esta mensagem não pode ser enviada no momento.')
            return redirect('wpp:message_detail', pk=pk)
        
        # Prévia dos envios
        contatos_preview = message.contatos.all()[:5]
        previews = []
        
        for contato in contatos_preview:
            previews.append({
                'contato': contato,
                'texto': message.campanha.processar_texto_para_contato(contato)
            })
        
        context = {
            'message': message,
            'previews': previews,
            'total_contatos': message.total_contatos,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk, company=request.user.company)
        
        if not message.pode_enviar():
            messages.error(request, 'Esta mensagem não pode ser enviada no momento.')
            return redirect('wpp:message_detail', pk=pk)
        
        # Marca como enviando
        message.status = 'enviando'
        message.data_envio_iniciado = timezone.now()
        message.save()
        
        try:
            # Cria logs para todos os contatos
            logs_created = []
            for contato in message.contatos.all():
                log, created = MessageLog.objects.get_or_create(
                    message=message,
                    contato=contato,
                    defaults={
                        'telefone': contato.telefone,
                        'texto_enviado': message.campanha.processar_texto_para_contato(contato),
                        'status': 'pendente'
                    }
                )
                if created:
                    logs_created.append(log)
            
            # TODO: Aqui será implementada a integração com Evolution API
            # Por enquanto, simula envio bem-sucedido
            for log in logs_created:
                log.status = 'enviado'
                log.enviado_em = timezone.now()
                log.response_api = {'status': 'success', 'simulated': True}
                log.save()
            
            # Atualiza estatísticas
            message.total_enviados = len(logs_created)
            message.status = 'enviada'
            message.data_envio_finalizado = timezone.now()
            message.save()
            
            messages.success(
                request, 
                f'Mensagem enviada com sucesso para {len(logs_created)} contatos!'
            )
            
        except Exception as e:
            # Em caso de erro
            message.status = 'erro'
            message.save()
            messages.error(request, f'Erro ao enviar mensagem: {str(e)}')
        
        return redirect('wpp:message_detail', pk=pk)