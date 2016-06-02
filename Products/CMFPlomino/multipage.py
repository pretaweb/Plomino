from Products.CMFPlomino.config import *
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zope.publisher.interfaces import IPublishTraverse
from zope.interface import implementer


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
        if request.path and request.path[-1] == 'validation_errors':
            self.validation = True
        else:
            self.validation = False

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

        if self.validation:
            return self.context.validation_errors(self.request)

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
                next_page = form._get_next_page(self.request, action='back')
                return self.redirect(next_page)

            errors = form.validateInputs(self.request)

            if errors:
                return self.context.EditDocument(request=self.request, page_errors=errors)

            # Any buttons progress the user through the form
            if current_page < (num_pages):
                next_page = form._get_next_page(self.request, action='continue')
                #REQUEST['plomino_current_page'] = next_page
                # Update the forms current page
                #setattr(self, 'plomino_current_page', next_page)

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
