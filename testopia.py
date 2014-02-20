#!/usr/bin/python
"""
The contents of this file are subject to the Mozilla Public
License Version 1.1 (the "License"); you may not use this file
except in compliance with the License. You may obtain a copy of
the License at http://www.mozilla.org/MPL/

Software distributed under the License is distributed on an "AS
IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
implied. See the License for the specific language governing
rights and limitations under the License.

The Original Code is the Bugzilla Testopia Python API Driver.

The Initial Developer of the Original Code is Airald Hapairai.
Portions created by Airald Hapairai are Copyright (C) 2008
Novell. All Rights Reserved.
Portions created by David Malcolm are Copyright (C) 2008 Red Hat.
All Rights Reserved.
Portions created by Will Woods are Copyright (C) 2008 Red Hat.
All Rights Reserved.
Portions created by Bill Peck are Copyright (C) 2008 Red Hat.
All Rights Reserved.

Contributor(s): Airald Hapairai
  David Malcolm <dmalcolm@redhat.com>
  Will Woods <wwoods@redhat.com>
  Bill Peck <bpeck@redhat.com>

The CookieTransport class is by Will Woods, based on code in
Python's xmlrpclib.Transport, which has this copyright notice:

# The XML-RPC client interface is
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.

Use this class to access Testopia via XML-RPC

Example on how to access this library,

from testopia import Testopia

t = Testopia.from_config('config.cfg')
t.testplan_get(10)

where config.cfg looks like:
[testopia]
username: jdoe@mycompany.com
password: jdoepassword
url:      https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi

Or, more directly:
t = Testopia('jdoe@mycompany.com',
             'jdoepassword',
             'https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi')             
t.testplan_get(10)

though this means you've embedded your login credentials in the source file.


Note: Python coding style guide does not advocate methods with more than 6-7
arguments. I've done this here with list, create, and update just to help.

-Airald Hapairai
"""

__author__="Airald Hapairai"
__date__="06/23/2008"
__version__="0.2.0.0"



import xmlrpclib, urllib2
from types import *
from datetime import datetime, time

from cookielib import CookieJar

class CookieTransport(xmlrpclib.Transport):
    '''A subclass of xmlrpclib.Transport that supports cookies.'''
    cookiejar = None
    scheme = 'http'

    # Cribbed from xmlrpclib.Transport.send_user_agent
    def send_cookies(self, connection, cookie_request):
        if self.cookiejar is None:
            self.cookiejar = cookielib.CookieJar()
        elif self.cookiejar:
            # Let the cookiejar figure out what cookies are appropriate
            self.cookiejar.add_cookie_header(cookie_request)
            # Pull the cookie headers out of the request object...
            cookielist=list()
            for h,v in cookie_request.header_items():
                if h.startswith('Cookie'):
                    cookielist.append([h,v])
            # ...and put them over the connection
            for h,v in cookielist:
                connection.putheader(h,v)
        else:
            pass

    # This is the same request() method from python 2.6's xmlrpclib.Transport,
    # with a couple additions noted below
    def request_with_cookies(self, host, handler, request_body, verbose=0):
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        # ADDED: construct the URL and Request object for proper cookie handling
        request_url = "%s://%s%s" % (self.scheme,host,handler)
        cookie_request  = urllib2.Request(request_url)

        self.send_request(h,handler,request_body)
        self.send_host(h,host)
        self.send_cookies(h,cookie_request) # ADDED. creates cookiejar if None.
        self.send_user_agent(h)
        self.send_content(h,request_body)

        errcode, errmsg, headers = h.getreply()

        # ADDED: parse headers and get cookies here
        # fake a response object that we can fill with the headers above
        class CookieResponse:
            def __init__(self,headers): self.headers = headers
            def info(self): return self.headers
        cookie_response = CookieResponse(headers)
        # Okay, extract the cookies from the headers
        self.cookiejar.extract_cookies(cookie_response,cookie_request)
        # And write back any changes
        if hasattr(self.cookiejar,'save'):
            try:
                self.cookiejar.save(self.cookiejar.filename)
            except Exception, e:
                pass

        if errcode != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock)

    # This is just python 2.7's xmlrpclib.Transport.single_request, with
    # send additions noted below to send cookies along with the request
    def single_request_with_cookies(self, host, handler, request_body, verbose=0):
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        # ADDED: construct the URL and Request object for proper cookie handling
        request_url = "%s://%s%s" % (self.scheme,host,handler)
        cookie_request  = urllib2.Request(request_url)

        try:
            self.send_request(h,handler,request_body)
            self.send_host(h,host)
            self.send_cookies(h,cookie_request) # ADDED. creates cookiejar if None.
            self.send_user_agent(h)
            self.send_content(h,request_body)

            response = h.getresponse(buffering=True)

            # ADDED: parse headers and get cookies here
            # fake a response object that we can fill with the headers above
            class CookieResponse:
                def __init__(self,headers): self.headers = headers
                def info(self): return self.headers

            cookie_response = CookieResponse(response.msg)
            # Okay, extract the cookies from the headers
            self.cookiejar.extract_cookies(cookie_response,cookie_request)
            # And write back any changes
            if hasattr(self.cookiejar,'save'):
                try:
                    self.cookiejar.save(self.cookiejar.filename)
                except Exception, e:
                    pass

            if response.status == 200:
                self.verbose = verbose
                return self.parse_response(response)
        except xmlrpclib.Fault:
            raise
        except Exception:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            self.close()
            raise

        #discard any response data and raise exception
        if (response.getheader("content-length", 0)):
            response.read()
        raise xmlrpclib.ProtocolError(
            host + handler,
            response.status, response.reason,
            response.msg,
            )

    # Override the appropriate request method
    if hasattr(xmlrpclib.Transport, 'single_request'):
        single_request = single_request_with_cookies # python 2.7+
    else:
        request = request_with_cookies # python 2.6 and earlier

class SafeCookieTransport(xmlrpclib.SafeTransport,CookieTransport):
    '''SafeTransport subclass that supports cookies.'''
    scheme = 'https'
    # Override the appropriate request method
    if hasattr(xmlrpclib.Transport, 'single_request'):
        single_request = CookieTransport.single_request_with_cookies # python 2.7+
    else:
        request = CookieTransport.request_with_cookies # python 2.6 and earlier

VERBOSE=0
DEBUG=0

class TestopiaError(Exception): pass

class TestopiaXmlrpcError(Exception):
    def __init__(self, verb, params, wrappedError):
        self.verb = verb
        self.params = params
        self.wrappedError = wrappedError

    def __str__(self):
        return "Error while executing cmd '%s' --> %s" \
               % ( self.verb + "(" + self.params + ")", self.wrappedError)
    
class Testopia(object):

    view_all=True # By default, a list returns at most 25 elements. We force here to see all.

    # (this decorator will require python 2.4 or later)
    @classmethod
    def from_config(cls, filename):
        """
        Make a Testopia instance from a config file, looking for a
        [testopia] stanza, containing 'login', 'password' and 'url'
        fields.

        For example, given config.txt containing:
          [testopia]
          login: jdoe@mycompany.com', 
          password: jdoepassword'
          url: https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi

        we can write scripts that avoid embedding user credentials in the
        source code:
          t = Testopia.from_config('config.txt')
          print t.environment_list()
        """
        from ConfigParser import SafeConfigParser
        cp = SafeConfigParser()
        cp.read([filename])
        kwargs = dict([(key, cp.get('testopia', key)) \
                       for key in ['username', 'password', 'url']])
        return Testopia(**kwargs)
    
    def __init__(self, username, password, url):
        """Initialize the Testopia driver.

        'username' -- string, the account to log into Testopia such as jdoe@mycompany.com,
        'password' -- string, the password for the username,
        'url' -- string, the URL of the XML-RPC interface 

        Example: t = Testopia('jdoe@mycompany.com', 
                              'jdoepassword'
                              'https://myhost.mycompany.com/bugzilla/tr_xmlrpc.cgi')
        """
        if url.startswith('https://'):
            self._transport = SafeCookieTransport()
        elif url.startswith('http://'):
            self._transport = CookieTransport()
        else:
            raise "Unrecognized URL scheme"
        self._transport.cookiejar = CookieJar()
        # print "COOKIES:", self._transport.cookiejar._cookies
        self.server = xmlrpclib.ServerProxy(url,
                                            transport = self._transport,
                                            verbose = VERBOSE)


        # Login, get a cookie into our cookie jar:
        loginDict = self.do_command("User.login", [dict(login=username,
                                                        password=password)])
        # Record the user ID in case the script wants this
        self.userId = loginDict['id']
        # print 'Logged in with cookie for user %i' % self.userId
        # print "COOKIES:", self._transport.cookiejar._cookies

    def _boolean_option(self, option, value):
        """Returns the boolean option when value is True or False, else ''

        Example: _boolean_option('isactive', True) returns " 'isactive': 1,"
        """
        if value or str(value) == 'False':
            if type(value) is not BooleanType:
                raise TestopiaError("The value for the option '%s' is not of boolean type." % option)
            elif value == False:
                return "\'%s\':0, " % option
            elif value == True:
                return "\'%s\':1, " % option
        return ''


    def _datetime_option(self, option, value):
        """Returns the string 'option': 'value' where value is a date object formatted
        in string as yyyy-mm-dd hh:mm:ss. If value is None, then we return ''.

        Example: self._time_option('datetime', datetime(2007,12,05,13,01,03))
        returns "'datetime': '2007-12-05 13:01:03'"
        """
        if value:
            if type(value) is not type(datetime(2000,01,01,12,00,00)):
                raise TestopiaError("The option '%s' is not a valid datetime object." % option)
            return "\'%s\':\'%s\', " % (option, value.strftime("%Y-%m-%d %H:%M:%S"))
        return ''


    def _list_dictionary_option(self, option, value):
        """Verifies that the value passed for the option is in the format of a list
        of dictionaries.

        Example: _list_dictionary_option('plan':[{'key1': 'value1', 'key2': 'value2'}])
        verifies that value is a list, then verifies that the content of value are dictionaries.
        """
        if value: # Verify that value is a type of list
            if type(value) is not ListType: # Verify that the content of value are dictionaries,
                raise TestopiaError("The option '%s' is not a valid list of dictionaries." % option)
            else:
                for item in value:
                    if type(item) is not DictType:
                        raise TestopiaError("The option '%s' is not a valid list of dictionaries." % option)
            return "\'%s\': %s" % (option, value)
        return ''

    _list_dict_op = _list_dictionary_option


    def _number_option(self, option, value):
        """Returns the string " 'option': value," if value is not None, else ''

        Example: self._number_option("isactive", 1) returns " 'isactive': 1,"
        """
        if value:
            if type(value) is not IntType:
                raise TestopiaError("The option '%s' is not a valid integer." % option)
            return "\'%s\':%d, " % (option, value)
        return ''


    def _number_no_option(self, number):
        """Returns the number in number. Just a totally useless wrapper :-)

        Example: self._number_no_option(1) returns 1
        """
        if type(number) is not IntType:
            raise TestopiaError("The 'number' parameter is not an integer.")
        return str(number)

    _number_noop = _number_no_option


    def _options_dict(self, *args):
        """Creates a wrapper around all the options into a dictionary format.

        Example, if args is ['isactive': 1,", 'description', 'Voyage project'], then
        the return will be {'isactive': 1,", 'description', 'Voyage project'}
        """
        return "{%s}" % ''.join(args)


    def _options_non_empty_dict(self, *args):
        """Creates a wrapper around all the options into a dictionary format and
        verifies that the dictionary is not empty.

        Example, if args is ['isactive': 1,", 'description', 'Voyage project'], then
        the return will be {'isactive': 1,", 'description', 'Voyage project'}.
        If args is empty, then we raise an error.
        """
        if not args:
            raise TestopiaError, "At least one variable must be set."
        return "{%s}" % ''.join(args)

    _options_ne_dict = _options_non_empty_dict


    def _string_option(self, option, value):
        """Returns the string 'option': 'value'. If value is None, then ''

        Example: self._string_option('description', 'Voyage project') returns
        "'description' : 'Voyage project',"
        """
        if value:
            if type(value) is not StringType:
                raise TestopiaError("The option '%s' is not a valid string." % option)
            return "\'%s\':\'%s\', " % (option, value)
        return ''


    def _string_no_option(self, option):
        """Returns the string 'option'.

        Example: self._string_no_option("description") returns "'description'"
        """
        if option:
            if type(option) is not StringType:
                raise TestopiaError("The option '%s' is not a valid string." % option)
            return "\'%s\'" % option
        return ''

    _string_noop = _string_no_option


    def _time_option(self, option, value):
        """Returns the string 'option': 'value' where value is a time object formatted in string as hh:mm:ss.
        If value is None, then we return ''.

        Example: self._time_option('time', time(12,00,03)) returns "'time': '12:00:03'"
        """
        if value:
            if type(value) is not type(time(12,00,00)):
                raise TestopiaError("The option '%s' is not a valid time object." % option)
            return "\'%s\':\'%s\', " % (option, value.strftime("%H:%M:%S"))
        return ''


    def _validate_search_operation_string(self, option, operation):
        """Validates the operation passed is a valid search operation.

        'operation' -- string, valid search operations

        Valid Search Operations:
            'equals',
            'notequals',
            'isnull',
            'isnotnull',
            'lessthan',
            'greaterthan',
            'regexp',
            'notregexp',
            'anywords',
            'allwords',
            'nowords',
        """
        VALID_SEARCH_OPERATIONS = ['equals', 'notequals', 'isnull',
                'isnotnull', 'lessthan', 'greaterthan', 'regexp',
                'notregexp', 'anywords', 'allwords', 'nowords',]
        if operation:
            if operation not in VALID_SEARCH_OPERATIONS:
                raise TestopiaError("Not a valid search operation.")
            else:
                return "\'%s\':\'%s\', " % (option, operation)
        return ''

    _search_op = _validate_search_operation_string


    def do_command(self, verb, args):
        """Submit a command to the server proxy.

        'verb' -- string, the xmlrpc verb,
        'args' -- list, the argument list,
        """
        params = ''
        for arg in args:
            params = ("%s" % str(arg), "%s, %s" % (params, str(arg)))[params!='']
        cmd = "self.server." + verb + "(" + params + ")"
        if DEBUG:
            print cmd
        #from pprint import pprint
        #pprint(self.server._ServerProxy__transport.cookiejar._cookies)
        try:
            return eval(cmd)
        except xmlrpclib.Error, e:
            raise TestopiaXmlrpcError(verb, params, e)
        
    ############################## Build #######################################


    def build_create(self, name, product_id, description=None, milestone=None,
                   isactive=None):
        """Create A New Build.

        'name' -- string, required value
        'product_id' -- integer, required value
        'description' -- string, optional
        'milestone' -- string, optional
        'isactive' -- boolean, optional

        Example: build_create(name='New Build', product_id=1)

        Result: A dictionary representing the new build
        """
        return self.do_command("Build.create", [self._options_dict(
                   self._string_option("name", name),
                   self._number_option("product_id", product_id),
                   self._string_option("description", description),
                   self._string_option("milestone", milestone),
                   self._boolean_option("isactive", isactive)
                   )])


    ############################## Environment ##################################


    def environment_create(self, product_id, isactive, name=None):
        """Create A New Environment

        'product_id' -- integer,
        'isactive' -- boolean,
        'name' -- string, optional

        Example: environment_create(1, True)

        Result: A dictionary representing the new environment
        """
        return self.do_command("Environment.create", [self._options_dict(
                   self._number_option('product_id', product_id),
                   self._boolean_option('isactive', isactive),
                   self._string_option('name', name)
                   )])

    ############################## Product ##################################


    def product_check_by_name(self, name):
        return self.do_command("TestopiaProduct.check_product", [self._string_noop(name)])

    def product_get_environments(self, product_id):
        """Get a list of environments for the given Product.

        'product_id' -- int,

        Example: product_get_environments(10)

        Result: A list of Environments dictionaries
        """
        return self.do_command("TestopiaProduct.get_environments", [self._number_noop(product_id)])

    def product_get_builds(self, product_id):
        """Get A List of Builds For An Existing Product.

        'product_id' -- integer, Must be greater than 0

        Example: product_get_builds(10)

        Result: A list of Build objects on success
        """
        return self.do_command("TestopiaProduct.get_builds", [self._number_noop(product_id)])


    ############################## Tag #######################################



    ############################## User ##################################

    def user_lookup_id_by_login(self, login):
        """Lookup A User ID By Its Login.

        'login' -- string, Cannot be null or empty string

        Example: user_lookup_id_by_login(login)

        Result: The user id for the respective login or 0 if an error occurs.
        """
        return self.do_command("User.lookup_id_by_login", [self._string_noop(login)])
        return self.do_command("User.lookup_login_by_id", [self._number_noop(id)])


    ############################## TestPlan ##################################


    def testplan_list(self, plan_id=None, plan_id_type=None,
                   name=None, name_type=None,
                   type_id=None, type_id_type=None,
                   creation_date=None, creation_date_type=None,
                   default_product_version=None, default_product_version_type=None,
                   author_id=None, author_id_type=None,
                   isactive=None, isactive_type=None,
                   product_id=None, product_id_type=None):
        """Get A List of TestPlans Based on A Query.

        'plan_id' -- integer, Must be greater than 0
        'plan_id_type' -- string, valid search operation,
        'name' -- string,
        'name_type' -- string, valid search operation,
        'type_id' -- integer,
        'type_id_type' -- string, valid search operation,
        'creation_date' -- string,
        'creation_date_type' -- string, valid search operation,
        'default_product_version' -- string,
        'default_product_version_type' -- string, valid search operation,
        'author_id' -- integer,
        'author_id_type' -- string, valid search operation,
        'isactive' -- boolean,
        'isactive_type' -- string, valid search operation,
        'product_id' -- integer,
        'product_id_type' -- string, valid search operation,

        Example: testplan_list(plan_id=2, planidtype='lessthan')

        Result: A list of TestPlan dictionaries
        """
        return self.do_command("TestPlan.list", [self._options_ne_dict(
                   self._number_option('plan_id', plan_id),
                   self._search_op('planidtype', plan_id_type),
                   self._string_option('name', name),
                   self._search_op('name_type', name_type),
                   self._number_option('type_id', type_id),
                   self._search_op('type_id', type_id_type),
                   self._datetime_option('creation_date', creation_date),
                   self._search_op('creation_date_type', creation_date_type),
                   self._string_option('default_product_version', default_product_version),
                   self._search_op('default_product_version_type', default_product_version_type),
                   self._number_option('author_id', author_id),
                   self._search_op('author_id', author_id_type),
                   self._boolean_option('isactive', isactive),
                   self._search_op('isactive_type', isactive_type),
                   self._number_option('product_id', product_id),
                   self._search_op('product_id', product_id_type),
                   self._boolean_option('viewall', self.view_all),
                   )])



    def testplan_get_categories(self, plan_id):
        """Get A List of Categories For An Existing Test Plan.

        'plan_id' -- integer, Must be greater than 0

        Example: testplan_get_categories(10)

        Result: A list of Category objects on success
        """
        return self.do_command("TestPlan.get_categories", [self._number_noop(plan_id)])



    def testplan_get_components(self, plan_id):
        """Get A List of Components For An Existing Test Plan.

        'plan_id' -- integer, Must be greater than 0

        Example: testplan_get_components(10)

        Result: A list of Component objects on success
        """
        return self.do_command("TestPlan.get_components", [self._number_noop(plan_id)])


    def testplan_get_test_cases(self, plan_id):
        """Get A List of Test Cases For An Existing Test Plan.

        'plan_id' -- integer, Must be greater than 0

        Example: testplan_get_test_cases(10)

        Result: A list of TestCase objects on success
        """
        return self.do_command("TestPlan.get_test_cases", [self._number_noop(plan_id)])


    def testplan_get_test_runs(self, plan_id):
        """Get A List of Test Runs For An Existing Test Plan.

        'plan_id' -- integer, Must be greater than 0

        Example: testplan_get_test_runs(10)

        Result: A list of TestRun objects on success
        """
        return self.do_command("TestPlan.get_test_runs", [self._number_noop(plan_id)])


    ############################## TestCase ##################################


    def testcase_get(self, case_id):
        """Get A TestCase by ID.

        'case_id' -- integer, Must be greater than 0

        Example: testcase_get(1)

        Result: A dictionary of key/value pairs for the attributes listed above
        """
        return self.do_command("TestCase.get", [self._number_noop(case_id)])


    ############################## TestRun ##################################


    def testrun_create(self, build_id, environment_id,
                   plan_id, summary, manager_id, plan_text_version=0,
                   notes=None, product_version='unspecified'):
        """Create A New TestRun.

        'build_id' -- integer, optional
        'environment_id' -- integer, optional
        'manager_id' -- integer, optional
        'plan_id' -- integer, optional
        'plan_text_version' -- integer, optional
        'summary' -- string, optional
        'notes' -- string, optional
        'product_version' -- integer, optional

        Example: testrun_create(1, 1, 1, 1, 'Summary')

        Result: A dictionary of key/value pairs representing the new testrun
        """
        return self.do_command("TestRun.create", [self._options_dict(
                   self._number_option('build_id', build_id),
                   self._number_option('environment_id', environment_id),
                   self._number_option('manager_id', manager_id),
                   self._number_option('plan_id', plan_id),
                   self._number_option('plan_text_version', plan_text_version),
                   self._string_option('summary', summary),
                   self._string_option('notes', notes),
                   self._string_option('product_version', product_version),
                   )])


    def testrun_update(self, run_id, status_id,build_id=None, 
                   environment_id=None,
                   manager_id=None, plan_text_version=None, summary=None,
                   notes=None, product_version=None, stop_date=None):
        """Update An Existing TestRun.

        'run_id' -- integer,
        'build_id' -- integer, optional
        'environment_id' -- integer, optional
        'manager_id' -- integer, optional
        'plan_text_version' -- integer, optional
        'summary' -- string, optional
        'notes' -- string, optional
        'product_version' -- integer, optional

        Example: testrun_update(1, 1, 1, 1, 'Summary')

        Result: The modified TestRun on success
        """
        return self.do_command("TestRun.update", [run_id, self._options_dict(
                   self._number_option('build_id', build_id),
                   self._number_option('environment_id', environment_id),
                   self._number_option('manager_id', manager_id),
                   self._number_option('plan_text_version', plan_text_version),
                   self._string_option('notes', notes),
                   self._number_option('product_version', product_version),
                   self._number_option('status', status_id),
                   self._datetime_option('stop_date', stop_date),
                   )])


    def testrun_get_test_cases(self, run_id):
        """Get A List of TestCases For An Existing Test Run.

        'run_id' -- integer,

        Example: testrun_get_test_cases(10)

        Result: A list of TestCase objects on success
        """
        return self.do_command("TestRun.get_test_cases", [self._number_noop(run_id)])


    ############################## TestCaseRun ##################################


    def testcaserun_create(self, assignee, build_id, case_id,
                           environment_id, run_id, case_text_version=None, notes=None):
        """Create A New TestCaseRun.

        'assignee' -- integer,
        'build_id' -- integer,
        'case_id' -- integer,
        'case_text_version' -- integer,
        'environment_id' -- integer,
        'run_id', integer,
        'notes' -- string, optional

        Example: testcaserun_create(1, 1, 1, 1, 1)

        Result: A dictionary representing the new test case run on success;
        on error, an XmlRpcException is thrown.
        """
        return self.do_command("TestCaseRun.create", [self._options_dict(
                   self._number_option('assignee', assignee),
                   self._number_option('build_id', build_id),
                   self._number_option('case_id', case_id),
                   self._number_option('case_text_version', case_text_version),
                   self._number_option('environment_id', environment_id),
                   self._number_option('run_id', run_id),
                   self._string_option('notes', notes),
                   )])


    def testcaserun_update(self, run_id, case_id, build_id, environment_id,
                    new_build_id=None,
                    new_environment_id=None,
                    case_run_status_id=None,
                    update_bugs=False,
                    assignee=None,
                    notes=None):
        """Create A New TestCaseRun.

        'run_id', integer,
        'case_id' -- integer,
        'build_id' -- integer,
        'environment_id' -- integer,
        'new_build_id' -- integer,
        'new_environment_id' -- integer,
        'case_run_status_id' -- integer, the id of the case status, optional
        'update_bugs' -- boolean, optional
        'assignee' -- integer, the id of the user, optional
        'notes' -- string, optional,

        Example: testcaserun_update(1, 1, 1, 1, 1)

        Result: The modified TestCaseRun on success; on failure, an XmlRpcException is thrown.

        Notes: When setting the case_run_status_id to 2 (PASS), the 'Tested by' is updated
        to the user hat is currently logged in.
        """
        return self.do_command("TestCaseRun.update", [
                   self._number_noop(run_id),
                   self._number_noop(case_id),
                   self._number_noop(build_id),
                   self._number_noop(environment_id),
                   self._options_dict(
                   self._number_option('build_id', new_build_id),
                   self._number_option('environment_id', new_environment_id),
                   self._number_option('case_run_status_id', case_run_status_id),
                   self._boolean_option('update_bugs', update_bugs),
                   self._number_option('assignee', assignee),
                   self._string_option('notes', notes),
                   )])
