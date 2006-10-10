# -*- coding: utf-8 -*-
#
# File: PlominoForm.py
#
# Copyright (c) 2006 by ['[Eric BREHAULT]']
# Generated: Fri Sep 29 17:50:38 2006
# Generator: ArchGenXML Version 1.5.1-svn
#            http://plone.org/products/archgenxml
#
# Zope Public License (ZPL)
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL). A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#

__author__ = """[Eric BREHAULT] <[ebrehault@gmail.com]>"""
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from Products.ATContentTypes.content.folder import ATFolder
from Products.CMFPlomino.config import *

##code-section module-header #fill in your manual code here
from Products.Archetypes.public import *
from Products.CMFCore import CMFCorePermissions
from Products.Archetypes.utils import make_uuid

from ZPublisher.HTTPResponse import HTTPResponse
from zLOG import LOG, ERROR

import re

import PlominoDocument
##/code-section module-header

schema = Schema((

    TextField(
        name='onOpenDocument',
        widget=TextAreaWidget(
            label="On open document",
            description="Action to take when the document is opned",
            label_msgid='CMFPlomino_label_onOpenDocument',
            description_msgid='CMFPlomino_help_onOpenDocument',
            i18n_domain='CMFPlomino',
        )
    ),

    TextField(
        name='onSaveDocument',
        widget=TextAreaWidget(
            label="On save document",
            description="Action to take when saving the document",
            label_msgid='CMFPlomino_label_onSaveDocument',
            description_msgid='CMFPlomino_help_onSaveDocument',
            i18n_domain='CMFPlomino',
        )
    ),

    TextField(
        name='FormLayout',
        allowable_content_types=('text/html',),
        widget=RichWidget(
            label="Form layout",
            description="The form layout. text with 'Plominofield' style correspond to the contained field elements",
            label_msgid='CMFPlomino_label_FormLayout',
            description_msgid='CMFPlomino_help_FormLayout',
            i18n_domain='CMFPlomino',
        ),
        default_output_type='text/html'
    ),

),
)

##code-section after-local-schema #fill in your manual code here
##/code-section after-local-schema

PlominoForm_schema = getattr(ATFolder, 'schema', Schema(())).copy() + \
    schema.copy()

##code-section after-schema #fill in your manual code here
##/code-section after-schema

class PlominoForm(ATFolder):
    """
    """
    security = ClassSecurityInfo()
    __implements__ = (getattr(ATFolder,'__implements__',()),)

    # This name appears in the 'add' box
    archetype_name = 'PlominoForm'

    meta_type = 'PlominoForm'
    portal_type = 'PlominoForm'
    allowed_content_types = ['PlominoField', 'PlominoAction', 'PlominoHidewhen'] + list(getattr(ATFolder, 'allowed_content_types', []))
    filter_content_types = 1
    global_allow = 0
    content_icon = 'PlominoForm.gif'
    immediate_view = 'base_view'
    default_view = 'base_view'
    suppl_views = ()
    typeDescription = "PlominoForm"
    typeDescMsgId = 'description_edit_plominoform'


    actions =  (


       {'action': "string:${object_url}/OpenForm",
        'category': "object",
        'id': 'compose',
        'name': 'Compose',
        'permissions': (CREATE_PERMISSION,),
        'condition': 'python:1'
       },


    )

    _at_rename_after_creation = True

    schema = PlominoForm_schema

    ##code-section class-header #fill in your manual code here
    ##/code-section class-header

    # Methods

    security.declareProtected(CREATE_PERMISSION, 'createDocument')
    def createDocument(self,REQUEST):
        """create a document using the forms submitted content
        """
	db = self.getParentDatabase()
	doc = db.createDocument()
	doc.setTitle( doc.id )
	doc.setItem('Form', self.getFormName())
	doc.saveDocument(REQUEST)

    security.declarePublic('getFields')
    def getFields(self):
        """get fields
        """
	return self.getFolderContents(contentFilter = {'portal_type' : ['PlominoField']})

    security.declarePublic('getHidewhenFormulas')
    def getHidewhenFormulas(self):
        """Get hidden formulae
        """
	return self.getFolderContents(contentFilter = {'portal_type' : ['PlominoHidewhen']})

    security.declarePublic('getFormName')
    def getFormName(self):
        """Return the form name
        """
	return self.Title()

    security.declarePublic('getParentDatabase')
    def getParentDatabase(self):
        """Get the database containing this form
        """
	return self.getParentNode()

    security.declareProtected(READ_PERMISSION, 'getFieldRender')
    def getFieldRender(self,doc,field,editmode):
        """Rendering the field
        """
	mode = field.getFieldMode()
	fieldName = field.Title()
	if mode=="EDITABLE":
		if doc is None:
			fieldValue = ""
		else:
			fieldValue = doc.getItem(fieldName)

		if editmode:
			ptsuffix="Edit"
		else:
			ptsuffix="Read"

		fieldType = field.FieldType
		try:
			exec "pt = self."+fieldType+"Field"+ptsuffix
		except Exception:
			exec "pt = self.DefaultField"+ptsuffix
		req = self.REQUEST
		# NOTE: for some reasons, sometimes, REQUEST does not have a RESPONSE
		# and it causes pt_render to fail (KeyError 'RESPONSE')
		# why ? I don't know (If you know, tell me please (ebrehault@gmail.com), I would be
		# happy to understand.
		# Anyhow, here is a small fix to avoid that.
		try:
			rep=self.REQUEST['RESPONSE']
		except Exception:
			self.REQUEST['RESPONSE']=HTTPResponse()
		return pt(fieldname=fieldName, fieldvalue=fieldValue, selection=field.getProperSelectionList(doc))

	if mode=="DISPLAY" or mode=="COMPUTED":
		# plominoDocument is the reserved name used in field formulae
		plominoDocument = doc
		try:
			exec "result = " + field.getFormula()
		except Exception:
			result = ""
		return str(result)

    security.declareProtected(READ_PERMISSION, 'displayDocument')
    def displayDocument(self,doc,editmode=False):
        """display the document using the form's layout
        """
	html_content = self.getField('FormLayout').get(self, mimetype='text/html')
	html_content = html_content.replace('\n', '')

	# remove the hidden content
	for hidewhen in self.getHidewhenFormulas():
		hidewhenName = hidewhen.Title
		# plominoDocument is the reserved name used in field formulae
		plominoDocument = doc
		try:
			exec "result = " + hidewhen.getObject().getFormula()
		except Exception:
			#if error, we hide anyway
			result = True
		start = '<span class="plominoHidewhenClass">start:'+hidewhenName+'</span>'
		end = '<span class="plominoHidewhenClass">end:'+hidewhenName+'</span>'
		if result:
			regexp = start+'.+'+end
			html_content = re.sub(regexp,'', html_content)
		else:
			html_content = html_content.replace(start, '')
			html_content = html_content.replace(end, '')

	#if editmode, we had a hidden field to handle the Form item value
	if editmode:
		html_content = "<input type='hidden' name='Form' value='"+self.getFormName()+"' />" + html_content

	# insert the fields with proper value and rendering
	for field in self.getFields():
		fieldName = field.Title
		#html_content = html_content.replace('#'+fieldName+'#', self.getFieldRender(doc, field.getObject(), editmode))
		html_content = html_content.replace('<span class="plominoFieldClass">'+fieldName+'</span>', self.getFieldRender(doc, field.getObject(), editmode))

	# insert the actions
	for action in self.getActions():
		actionName = action.Title
		actionDisplay = action.getObject().ActionDisplay
		try:
			exec "pt = self."+actionDisplay+"Action"
		except Exception:
			pt = self.LINKAction
		action_render = pt(plominoaction=action, plominotarget=doc)
		#html_content = html_content.replace('#Action:'+actionName+'#', action_render)
		html_content = html_content.replace('<span class="plominoActionClass">'+actionName+'</span>', action_render)

	return html_content

    security.declarePublic('formLayout')
    def formLayout(self):
        """return the form layout in edit mode (used to compose a new
        document)
        """
	return self.displayDocument(None, True)

    security.declarePublic('getActions')
    def getActions(self):
        """Get actions
        """
	return self.getFolderContents(contentFilter = {'portal_type' : ['PlominoAction']})

    security.declarePublic('at_post_edit_script')
    def at_post_edit_script(self):
        """clean up the layout before saving
        """
	# clean up the form layout field
	html_content = self.getField('FormLayout').get(self, mimetype='text/html')
	regexp = '<span class="plominoFieldClass"></span>'
	html_content = re.sub(regexp,'', html_content)
	regexp = '<span class="plominoActionClass"></span>'
	html_content = re.sub(regexp,'', html_content)
	regexp = '<span class="plominoHidewhenClass"></span>'
	self.setFormLayout(html_content)



registerType(PlominoForm, PROJECTNAME)
# end of class PlominoForm

##code-section module-footer #fill in your manual code here
##/code-section module-footer



