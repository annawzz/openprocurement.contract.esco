# -*- coding: utf-8 -*-
from copy import deepcopy
from uuid import uuid4
from datetime import timedelta
from openprocurement.contracting.esco.models import Contract
from openprocurement.api.utils import get_now

# ContractTest


def simple_add_esco_contract(self):
    u = Contract(self.initial_data)
    u.contractID = "UA-C"

    assert u.id == self.initial_data['id']
    assert u.doc_id == self.initial_data['id']
    assert u.rev is None

    u.store(self.db)

    assert u.id == self.initial_data['id']
    assert u.rev is not None

    fromdb = self.db.get(u.id)

    assert u.contractID == fromdb['contractID']
    assert u.doc_type == "Contract"

    u.delete_instance(self.db)

# ContractResourceTest

def esco_contract_milestones_check(self):
    response = self.app.get('/contracts')
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(len(response.json['data']), 0)

    response = self.app.post_json('/contracts', {"data": self.initial_data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    contract = response.json['data']
    self.assertEqual(contract['status'], 'active')

    response = self.app.get('/contracts/{}'.format(contract['id']))
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.status, '200 OK')
    data = response.json['data']['milestones']
    self.assertEqual(len(data), 8)
    sequenceNumber = 1
    for milestone in data:
        if sequenceNumber == 1:
            self.assertEqual(milestone['status'], 'pending')
        else:
            self.assertEqual(milestone['status'], 'scheduled')
        self.assertEqual(milestone['sequenceNumber'], sequenceNumber)
        sequenceNumber += 1


def create_contract(self):
    response = self.app.get('/contracts')
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(len(response.json['data']), 0)

    response = self.app.post_json('/contracts', {"data": self.initial_data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    contract = response.json['data']
    self.assertEqual(contract['status'], 'active')

    response = self.app.get('/contracts/{}'.format(contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(set(response.json['data']), set(contract))
    self.assertEqual(response.json['data'], contract)

    data = deepcopy(self.initial_data)
    data['id'] = uuid4().hex
    response = self.app.post_json('/contracts?opt_jsonp=callback', {"data": data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/javascript')
    self.assertIn('callback({"', response.body)

    data['id'] = uuid4().hex
    response = self.app.post_json('/contracts?opt_pretty=1', {"data": data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    self.assertIn('{\n    "', response.body)

    data['id'] = uuid4().hex
    response = self.app.post_json('/contracts', {"data": data, "options": {"pretty": True}})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    self.assertIn('{\n    "', response.body)

    # broker has no permissions to create contract
    self.app.authorization = ('Basic', ('broker', ''))
    response = self.app.post_json('/contracts', {"data": self.initial_data}, status=403)
    self.assertEqual(response.status, '403 Forbidden')


def create_contract_generated(self):
    data = self.initial_data.copy()
    data.update({'id': uuid4().hex, 'doc_id': uuid4().hex, 'contractID': uuid4().hex})
    response = self.app.post_json('/contracts', {'data': data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    contract = response.json['data']
    self.assertEqual(set(contract), set([
        u'id', u'dateModified', u'contractID', u'status', u'suppliers',
        u'contractNumber', u'period', u'dateSigned', u'value', u'awardID',
        u'items', u'owner', u'tender_id', u'procuringEntity', u'contractType',
        u'NBUdiscountRate', u'value', u'description', u'title', u'milestones',
        u'amountPaid']))
    self.assertEqual(data['id'], contract['id'])
    self.assertNotEqual(data['doc_id'], contract['id'])
    self.assertEqual(data['contractID'], contract['contractID'])


def patch_contract_NBUdiscountRate(self):
    response = self.app.post_json('/contracts', {"data": self.initial_data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    contract = response.json['data']
    tender_token = self.initial_data['tender_token']
    self.assertIn('NBUdiscountRate', response.json['data'])
    self.assertEqual(contract['NBUdiscountRate'], self.initial_data['NBUdiscountRate'])
    self.assertNotEqual(response.json['data']['NBUdiscountRate'], 0.33)

    response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(contract['id'], tender_token),
                                   {'data': ''})
    self.assertEqual(response.status, '200 OK')
    token = response.json['access']['token']

    # NBUdiscountRate field forbidden for patch
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(contract['id'], token),
                                   {'data': {'NBUdiscountRate': 0.33}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json, None)

    response = self.app.get('/contracts/{}'.format(contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['NBUdiscountRate'], self.initial_data['NBUdiscountRate'])

    # check NBUdiscountRate patch for teminated contract
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(contract['id'], token),
                                   {"data": {"status": "terminated",
                                             "terminationDetails": "sink"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['status'], 'terminated')
    self.assertEqual(response.json['data']['terminationDetails'], 'sink')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(contract['id'], token),
                                   {'data': {'NBUdiscountRate': 0.33}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.get('/contracts/{}'.format(contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['NBUdiscountRate'], self.initial_data['NBUdiscountRate'])


def contract_type_check(self):
    expected_contract_type = getattr(self, 'contract_type')
    response = self.app.post_json('/contracts', {"data": self.initial_data})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.content_type, 'application/json')
    contract = response.json['data']
    tender_token = self.initial_data['tender_token']
    self.assertIn('contractType', response.json['data'])
    self.assertEqual(contract['contractType'], expected_contract_type)

    response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(contract['id'], tender_token),
                                   {'data': ''})
    self.assertEqual(response.status, '200 OK')
    token = response.json['access']['token']

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(contract['id'], token),
        {'data': {'contractType': 'common'}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.body, 'null')

    response = self.app.get('/contracts/{}'.format(contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertNotEqual(response.json['data']['contractType'], 'common')
    self.assertEqual(response.json['data']['contractType'], 'esco')


def patch_tender_contract(self):
    response = self.app.patch_json('/contracts/{}'.format(
        self.contract['id']), {"data": {"title": "New Title"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    tender_token = self.initial_data['tender_token']
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], tender_token), {"data": {"title": "New Title"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(
        self.contract['id'], tender_token), {'data': ''})
    self.assertEqual(response.status, '200 OK')
    token = response.json['access']['token']

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"title": "New Title"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['title'], "New Title")

    # can't patch contract amountPaid amount, currency and vat
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {
            "amountPaid": {"amount": 900, "currency": "USD", "valueAddedTaxIncluded": False}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.body, 'null')

    # check milestone amountPaid change
    # get correct pending milestone
    response = self.app.get('/contracts/{}'.format(self.contract_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    milestone = response.json['data']['milestones'][0]
    # make sure it's pending milestone!
    self.assertEqual(milestone['status'], 'pending')

    # update amountPaid of milestone
    response = self.app.patch_json('/contracts/{}/milestones/{}?acc_token={}'.format(
        self.contract_id, milestone['id'], token), {'data': {
            "amountPaid": {"amount": 100000}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json["data"]["amountPaid"]["amount"], 100000)

    # contract amountPaid.amount not changed, equal sum of milestones.amountPaid
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {
            "amountPaid": {"amount": 900, "currency": "USD", "valueAddedTaxIncluded": False}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.body, 'null')

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['amountPaid']['amount'], 100000)
    self.assertEqual(response.json['data']['amountPaid']['currency'], "UAH")
    self.assertEqual(response.json['data']['amountPaid']['valueAddedTaxIncluded'], True)

    # can't patch value amount, currency and vat
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"value": {'amount': 1000}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.body, 'null')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"value": {"currency": "USD", "valueAddedTaxIncluded": False}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.body, 'null')

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    # value is calculated from milestones
    milestones_value = sum(x['value']['amount'] for x in response.json['data']['milestones'])
    self.assertEqual(response.json['data']['value']['amount'], round(milestones_value, 2))
    self.assertEqual(response.json['data']['value']['currency'], self.initial_data['value']['currency'])
    self.assertEqual(response.json['data']['value']['valueAddedTaxIncluded'], self.initial_data['value']['valueAddedTaxIncluded'])

    # can't patch milestones from contract
    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    milestones = response.json['data']['milestones']

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"milestones": []}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.body, 'null')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"milestones": [{'title': 'new title'}, {}, {}]}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.body, 'null')

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertNotEqual(response.json['data']['milestones'][0]['title'], 'new title')
    self.assertEqual(len(response.json['data']['milestones']), len(milestones))
    self.assertEqual(response.json['data']['milestones'], milestones)

    custom_period_start_date = get_now().isoformat()
    custom_period_end_date = (get_now() + timedelta(days=3)).isoformat()
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {
            "period": {'startDate': custom_period_start_date,
                       'endDate': custom_period_end_date}}})
    self.assertEqual(response.status, '200 OK')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {
            "status": "terminated",
            "terminationDetails": "sink"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['status'], 'terminated')
    self.assertEqual(response.json['data']['terminationDetails'], 'sink')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"status": "active"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"title": "fff"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.patch_json('/contracts/some_id', {"data": {"status": "active"}}, status=404)
    self.assertEqual(response.status, '404 Not Found')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['status'], 'error')
    self.assertEqual(response.json['errors'], [
        {u'description': u'Not Found', u'location':
         u'url', u'name': u'contract_id'}
    ])

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "terminated")
    # value is calculated from milestones
    milestones_value = sum(x['value']['amount'] for x in response.json['data']['milestones'])
    self.assertEqual(response.json['data']['value']['amount'], round(milestones_value, 2))
    self.assertEqual(response.json['data']['period']['startDate'], custom_period_start_date)
    self.assertEqual(response.json['data']['period']['endDate'], custom_period_end_date)
    self.assertEqual(response.json['data']['amountPaid']['amount'], 100000)
    self.assertEqual(response.json['data']['terminationDetails'], 'sink')


def contract_administrator_change(self):
    response = self.app.patch_json('/contracts/{}'.format(self.contract['id']),
                                   {'data': {'mode': u'test',
                                             "suppliers": [{
                                                "contactPoint": {
                                                    "email": "fff@gmail.com",
                                                },
                                                "address": {"postalCode": "79014"}
                                             }],
                                             'procuringEntity': {"identifier": {"id": "11111111"},
                                                                 "contactPoint": {"telephone": "102"}}
                                             }})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']['mode'], u'test')
    self.assertEqual(response.json['data']["procuringEntity"]["identifier"]["id"], "11111111")
    self.assertEqual(response.json['data']["procuringEntity"]["contactPoint"]["telephone"], "102")
    self.assertEqual(response.json['data']["suppliers"][0]["contactPoint"]["email"], "fff@gmail.com")
    self.assertEqual(
        response.json['data']["suppliers"][0]["contactPoint"]["telephone"],
        self.initial_data['suppliers'][0]['contactPoint']['telephone']
    )
    self.assertEqual(response.json['data']["suppliers"][0]["address"]["postalCode"], "79014")
    self.assertEqual(response.json['data']["suppliers"][0]["address"]["countryName"], u"Україна") # old field value left untouchable
    # administrator has permissions to update only: mode, procuringEntity, suppliers
    response = self.app.patch_json('/contracts/{}'.format(self.contract['id']), {'data': {
        'value': {'amount': 100500},
        'id': '1234' * 8,
        'owner': 'kapitoshka',
        'contractID': "UA-00-00-00",
        'dateSigned': get_now().isoformat(),
    }})
    self.assertEqual(response.body, 'null')

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    # value is calculated from milestones
    milestones_value = sum(x['value']['amount'] for x in response.json['data']['milestones'])
    self.assertEqual(response.json['data']['value']['amount'], round(milestones_value, 2))
    self.assertEqual(response.json['data']['id'], self.initial_data['id'])
    self.assertEqual(response.json['data']['owner'], self.initial_data['owner'])
    self.assertEqual(response.json['data']['contractID'], self.initial_data['contractID'])
    self.assertEqual(response.json['data']['dateSigned'], self.initial_data['dateSigned'])


def contract_status_change(self):
    tender_token = self.initial_data['tender_token']

    response = self.app.get('/contracts/{}'.format(self.contract['id']))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], tender_token), {"data": {"status": "active"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')

    response = self.app.patch_json('/contracts/{}/credentials?acc_token={}'.format(
        self.contract['id'], tender_token), {'data': ''})
    self.assertEqual(response.status, '200 OK')
    token = response.json['access']['token']

    # active > terminated allowed
    # set amountPaid - TODO - check rules later
    # get correct pending milestone
    response = self.app.get('/contracts/{}'.format(self.contract_id))
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    milestone = response.json['data']['milestones'][0]
    # make sure it's pending milestone!
    self.assertEqual(milestone['status'], 'pending')

    response = self.app.patch_json('/contracts/{}/milestones/{}?acc_token={}'.format(
        self.contract_id, milestone['id'], token), {'data': {
            "amountPaid": {"amount": 100000}}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json["data"]["amountPaid"]["amount"], 100000)

    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"status": "terminated"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['status'], 'terminated')

    # terminated > active not allowed
    response = self.app.patch_json('/contracts/{}?acc_token={}'.format(
        self.contract['id'], token), {"data": {"status": "active"}}, status=403)
    self.assertEqual(response.status, '403 Forbidden')
