from Products.CMFPlomino.config import *
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implementer

ACTIONS = (
    'validation_errors',
    'tojson',
    'statusmessage_load',
    'computedynamiccontent',
)


@implementer(IPublishTraverse)
class PageView(BrowserView):

    def publishTraverse(self, request, name):
        # stop traversing, we have arrived
        request['TraversalRequestNameStack'] = []
        # return self so the publisher calls this view
        return self

    def __init__(self, context, request):
        """Once we get to __call__, the path is lost so we
        capture it here on initialization
        """
        super(PageView, self).__init__(context, request)

        # Certain URLs should be handled outside paging
        # XXX: Do this better
        self.action = None
        if request.path:
            if request.path[-1] in ACTIONS:
                self.action = request.path[-1]

        # Default page is page 1
        self.page = 1
        # Ignore everything past the first page
        if request.path:
            try:
                self.page = int(request.path[0])
            except ValueError:
                self.page = 1

    def __call__(self):
        # Check permissions here?
        self.checkPermission()

        # XXX: do this better
        if self.action:
            if self.action == 'validation_errors':
                return self.context.validation_errors(self.request)
            elif self.action == 'tojson':
                return self.context.tojson(self.request)
            elif self.action == 'statusmessage_load':
                return self.context.statusmessage_load(self.request)
            elif self.action == 'computedynamiccontent':
                return self.context.computedynamiccontent(self.request)

        # Set the current page
        self.request['plomino_current_page'] = self.page

        if self.context.portal_type == 'PlominoDocument':
            return self._handle_document()
        else:
            return self._handle_form()

    def redirect(self, page):
        url = self.context.absolute_url()
        # Tidy up the URL
        url = url.replace('plomino_documents/', '')
        return self.request.RESPONSE.redirect('%s/page/%s' % (url, page))

    def checkPermission(self):
        """You might want to do other stuff"""
        # raise Unauthorized
        pass

    def _handle_document(self):
        """ Open/Edit the existing document """
        form = self.context.getForm()

        # Get multi page information
        current_page = form._get_current_page()
        num_pages = form._get_num_pages()

        # If they have gone past the end of the form, send them back
        if current_page > num_pages:
            return self.redirect(num_pages)

        # Handle POST requests differently.
        if self.request['REQUEST_METHOD'] == 'POST':
            # Look up the form. This might be the context, or the parent form
            # or a value from the request

            if 'back' in self.request.form:
                next_page = form._get_next_page(self.request, doc=self.context, action='back')
                return self.redirect(next_page)

            # Handle linking
            linkto = False
            for key in self.request.form.keys():
                if key.startswith('plominolinkto-'):
                    linkto = key.replace('plominolinkto-', '')
                    next_page = form._get_next_page(self.request, doc=self.context, action='linkto', target=linkto)
                    return self.redirect(next_page)

            # Pass in the current doc as well. This ensures that fields on other
            # pages are included (possibly needed for calculations)
            errors = form.validateInputs(self.request, doc=self.context)

            if errors:
                return self.context.EditDocument(request=self.request, page_errors=errors)

            # Any buttons progress the user through the form
            # XXX: We need to handle other types of buttons here
            if current_page < (num_pages):
                next_page = form._get_next_page(self.request, doc=self.context, action='continue')
            else:
                # Don't go past the end of the form
                next_page = num_pages

            # execute the beforeSave code of the form
            error = None
            try:
                error = self.context.runFormulaScript(
                        SCRIPT_ID_DELIMITER.join(['form', form.id, 'beforesave']),
                        self.context,
                        form.getBeforeSaveDocument)
            except PlominoScriptException, e:
                e.reportError('Form submitted, but beforeSave formula failed')

            if error:
                errors.append({'field': 'beforeSave', 'error': error})
                # Stay on this page
                return self.context.EditDocument(request=self.request, page_errors=errors)

            # Now save and move forwards
            self.context.setItem('Form', form.getFormName())

            # process editable fields (we read the submitted value in the request)
            form.readInputs(self.context, self.request, process_attachments=True)

            # refresh computed values, run onSave, reindex. Should never be creation.
            self.context.save(form, False)

            # If there is a redirect, redirect to it:
            redirect = self.request.get('plominoredirecturl')
            if not redirect:
                redirect = self.context.getItem("plominoredirecturl")

            if redirect:
                return self.request.RESPONSE.redirect(redirect)

            # Otherwise continue to the next page of the document
            return self.redirect(next_page)

        else:
            # GET request
            pass

        return self.context.EditDocument(request=self.request)

    def _handle_form(self):
        """ Use the OpenForm """
        form = self.context.getForm()

        # Get multi page information
        current_page = form._get_current_page()
        num_pages = form._get_num_pages()

        if self.request['REQUEST_METHOD'] == 'POST':
            # If back is in the form, page backwards
            if 'back' in self.request.form:
                self.request['plomino_current_page'] = form._get_next_page(self.request, action='back')
                return form.OpenForm(request=self.request)

            # Handle linking
            for key in self.request.form.keys():
                if key.startswith('plominolinkto-'):
                    linkto = key.replace('plominolinkto-', '')
                    self.request['plomino_current_page'] = form._get_next_page(self.request, action='linkto', target=linkto)
                    return form.OpenForm(request=self.request)

            errors = form.validateInputs(self.request)

            # We can't continue if there are error:
            if errors:
                # inject these into the form
                return form.OpenForm(request=self.request, page_errors=errors)

            # If next or continue is the form, page forwards if the form is valid
            if 'next' in self.request.form or 'continue' in self.request.form:
                if current_page < (num_pages):
                    self.request['plomino_current_page'] = form._get_next_page(self.request, action='continue')
                    return form.OpenForm(request=self.request)

            # Otherwise create the document
            return form.createDocument(self.request)

        else:
            return form.OpenForm(request=self.request)


@implementer(IPublishTraverse)
class ReadPageView(PageView):

    def _handle_document(self):
        form = self.context.getForm()

        # Get multi page information
        current_page = form._get_current_page()
        num_pages = form._get_num_pages()

        # If there is something in the form
        if self.request.form:
            # If they have gone past the end of the form, send them back
            if current_page > num_pages:
                return self.redirect(num_pages)

            if 'back' in self.request.form:
                next_page = form._get_next_page(self.request, doc=self.context, action='back')
                return self.redirect(next_page)

            # Handle linking
            linkto = False
            for key in self.request.form.keys():
                if key.startswith('plominolinkto-'):
                    linkto = key.replace('plominolinkto-', '')
                    next_page = form._get_next_page(self.request, doc=self.context, action='linkto', target=linkto)
                    return self.redirect(next_page)

            # Any buttons progress the user through the form
            # XXX: We need to handle other types of buttons here
            if current_page < (num_pages):
                next_page = form._get_next_page(self.request, doc=self.context, action='continue')
            else:
                # Don't go past the end of the form
                next_page = num_pages

            return self.redirect(next_page)

        return self.context.OpenDocument()

    def redirect(self, page):
        url = self.context.absolute_url()
        # Tidy up the URL
        url = url.replace('plomino_documents/', '')
        return self.request.RESPONSE.redirect('%s/pageview/%s' % (url, page))
