from testopia import *
import re

class YpTestopia(Testopia):

    def __init__(self, url, user, password, build_branch, build_commit, milestone, environment, product_version, build_date=None):
        self.url = url
        self.user = user
        self.password = password
        self.build_branch = build_branch
        self.build_commit = build_commit
        self.testrun_auto_summary = build_date + ' - ' + 'automated'
        self.automation_user_id = 1 # we could determine this automatically
        self.milestone = milestone
        self.environment = environment
        self.environment_placeholder = 'placeholder - ' + self.environment
        self.build_date = build_date
        self.product_version = product_version
        self.reset_product()
        super(YpTestopia, self).__init__(user, password, url)


    def reset_caserun(self):
        self.testcase_alias = None
        self.testcase_object = None
        self.testcase_id = None
        self.caserun_initiated = False

    def reset_product(self):
        self.reset_caserun()
        self.product_name = None
        self.product_object = None
        self.product_id = None
        self.testplan_object = None
        self.testplan_id = None
        self.testplan_name = None
        self.environment_object = None
        self.environment_id = None
        self.build_object = None
        self.build_id = None
        self.testrun_auto_object = None
        self.testrun_auto_id = None
        self.product_initiated = False

    def copy(self):
        return YpTestopia(url=self.url, user=self.user, password=self.password, build_branch=self.build_branch, build_commit=self.build_commit, milestone=self.milestone, environment=self.environment, product_version=self.product_version, build_date=self.build_date)

    def init_product(self, product_name):
        self.reset_caserun()
        self.reset_product()

        self.product_name = product_name
        self.product_object = self.product_check_by_name(self.product_name)
        if not self.product_object:
            print "ERROR: Could not find Product"
            return None
        self.product_id = self.product_object['id']

        self.testplan_object = self._get_testplan_object()
        if not self.testplan_object:
            print "ERROR: Could not find Testplan"
            return None
        self.testplan_id = self.testplan_object['plan_id']
        self.testplan_name = self.testplan_object['name']

        self.environment_object = self._get_environment_object() # what happens if the evnvironment is not active?
        if not self.environment_object:
            print "Environment does not exist!"
            self.environment_object = self._create_environment_placeholder()
        self.environment_id = self.environment_object['environment_id']

        self.build_object = self._get_build_object() #  what happens if the build is not active?
        if not self.build_object:
            print "Build does not exist!"
            self.build_object = self._create_build()
        self.build_id = self.build_object['build_id']

        self.testrun_auto_object = self._get_testrun_auto_object()
        if not self.testrun_auto_object:
            print "Test Run does not exist!"
            self.testrun_auto_object = self._create_testrun()
        self.testrun_auto_id = self.testrun_auto_object['run_id']
        self.product_initiated = True
        return True

    def init_caserun_by_alias(self, testcase_alias):
        self.reset_caserun()
        if not self.product_initiated:
            print "ERROR: Cannot initiate caserun because product is not initiated"
            return None
        self.testcase_alias = testcase_alias
        self.testcase_object = self._get_testcase_object()
        self.testcase_id = self.testcase_object['case_id']
        self.caserun_initiated = True
        return True

    def init_caserun_by_id(self, testcase_id):
        self.reset_caserun()
        if not self.product_initiated:
            print "ERROR: Cannot initiate caserun because product is not initiated"
            return None
        self.testcase_id = testcase_id # What happens when testcase_id is not in the current testplan/product/does not exist at all? :(
        self.testcase_object = self.testcase_get(self.testcase_id)
        self.caserun_initiated = True
        return True

    def execute_caserun(self, caserun_status):
        if not self.caserun_initiated:
            print "ERROR: Cannot execute uninitiated caserun"
            return None
        if not self._check_testcase_in_testrun(): # What if TestRun is STOPPED?
            print "Case Run does not exist!"
            self._add_caserun()
        self._update_caserun(caserun_status) # What if status is not valid?


    def _check_for_single_result(self, check_list):
        if len(check_list) == 1:
            return check_list[0]
        if len(check_list) == 0:
            return None
        if len(check_list) > 1:
            raise Exception("List has multiple elements")

    def _get_testplan_object(self):
        testplan_list = self.testplan_list(product_id=self.product_id)
        regex = re.compile("^%s:.*%s branch" % (self.product_name, self.build_branch), re.IGNORECASE)
        testplan_object = [testplan for testplan in testplan_list for m in [regex.search(str(testplan['name']))] if m]
        return self._check_for_single_result(testplan_object)

    def _get_testcase_object(self): # make this work with provided testcase_id ? As a check if testcase_id is in the right product and test plan.
        testcase_list = self.testplan_get_test_cases(self.testplan_id)
        regex = re.compile("^%s$" % self.testcase_alias, re.IGNORECASE)
        automated_testcase = [testcase for testcase in testcase_list if testcase['isautomated'] == 1] # we need a check for CONFIRMED status only
        testcase_object = [testcase for testcase in automated_testcase if testcase.get('alias') for m in [regex.search(str(testcase['alias']))] if m]
        return self._check_for_single_result(testcase_object)

    def _get_environment_object(self):
        environment_list = self.product_get_environments(self.product_id)
        regex = re.compile("%s$" % self.environment, re.IGNORECASE)
        environment_object = [environment for environment in environment_list for m in [regex.search(str(environment['name']))] if m]
        return  self._check_for_single_result(environment_object)

    def _create_environment_placeholder(self):
        print "Creating Environment"
        return self.environment_create(product_id=self.product_id, isactive=True, name=self.environment_placeholder)

    def _get_build_object(self):
        build_list = self.product_get_builds(self.product_id)
        commit_regex = re.compile("%s" % self.build_commit, re.IGNORECASE)
        # We need a better way to find the correct build if commit matching gives more than 1 result (small theoretical probability though)
        build_object = [build for build in build_list for m in [commit_regex.search(str(build['name']))] if m]
        if len(build_object) > 1:
            branch_regex = re.compile("%s" % self.build_branch, re.IGNORECASE)
            build_object_new = [build for build in build_list for m in [branch_regex.search(str(build['name']))] if m]
            build_object = build_object_new
        return self._check_for_single_result(build_object)

    def _create_build(self):
        print "Creating build"
        return self.build_create(name="%s:%s" % (self.build_branch, self.build_commit), product_id=self.product_id, description=self.build_date, milestone=self.milestone, isactive=True)

    def _get_testrun_auto_object(self):
        testrun_list = self.testplan_get_test_runs(self.testplan_id)
        summary_regex = re.compile('automated', re.IGNORECASE)
        testrun_object = [testrun for testrun in testrun_list if testrun['build_id'] == self.build_id if testrun['environment_id'] == self.environment_id for m in [summary_regex.search(str(testrun['summary']))] if m]
        return self._check_for_single_result(testrun_object)

    def _create_testrun(self):
        print "Creating Test Run"
        return self.testrun_create(build_id=self.build_id, environment_id=self.environment_id, plan_id=self.testplan_id, summary=self.testrun_auto_summary, manager_id=self.automation_user_id, product_version=self.product_version)

    def _check_testcase_in_testrun(self):
        testcase_list = self.testrun_get_test_cases(self.testrun_auto_id)
        testcase_object = [testcase for testcase in testcase_list if testcase['case_id'] == self.testcase_id]
        if testcase_object:
            return True
        else:
            return False

    def _add_caserun(self):
        print "Creating caserun"
        self.testcaserun_create(assignee=self.automation_user_id, build_id=self.build_id, case_id=self.testcase_id, environment_id=self.environment_id, run_id=self.testrun_auto_id)

    def _update_caserun(self, caserun_status):
        print "updating caserun" 
        self.testcaserun_update(run_id=self.testrun_auto_id, case_id=self.testcase_id, build_id=self.build_id, environment_id=self.environment_id, case_run_status_id=caserun_status)




