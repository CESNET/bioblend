"""
Contains possible interactions with the Galaxy workflow invocations
"""
import logging
import time

from bioblend import (
    CHUNK_SIZE,
    TimeoutException,
)
from bioblend.galaxy.client import Client

log = logging.getLogger(__name__)

INVOCATION_TERMINAL_STATES = {'cancelled', 'failed', 'scheduled'}
# Invocation non-terminal states are: 'new', 'ready'


class InvocationClient(Client):
    def __init__(self, galaxy_instance):
        self.module = 'invocations'
        super().__init__(galaxy_instance)

    def get_invocations(self, workflow_id=None, history_id=None, user_id=None,
                        include_terminal=True, limit=None, view='collection',
                        step_details=False):
        """
        Get a list containing all the workflow invocations corresponding to the
        specified workflow.

        :type workflow_id: str
        :param workflow_id: Encoded workflow ID to filter on

        :type history_id: str
        :param history_id: Encoded history ID to filter on

        :type user_id: str
        :param user_id: Encoded user ID to filter on. This must be
                        your own user ID if your are not an admin user.

        :type limit: int
        :param limit: Maximum number of invocations in the query result.

        :type include_terminal: bool
        :param include_terminal: Whether to include terminal states.

        :type view: str
        :param view: Level of detail to return per invocation, either
                     'element' or 'collection'.

        :type step_details: bool
        :param step_details: If 'view' is 'element', also include details
                             on individual steps.

        :rtype: list
        :return: A list of workflow invocations.
          For example::

            [{'history_id': '2f94e8ae9edff68a',
              'id': 'df7a1f0c02a5b08e',
              'model_class': 'WorkflowInvocation',
              'state': 'new',
              'update_time': '2015-10-31T22:00:22',
              'uuid': 'c8aa2b1c-801a-11e5-a9e5-8ca98228593c',
              'workflow_id': '03501d7626bd192f'}]
        """
        params = {
            'include_terminal': include_terminal,
            'view': view,
            'step_details': step_details
        }
        if workflow_id:
            params['workflow_id'] = workflow_id
        if history_id:
            params['history_id'] = history_id
        if user_id:
            params['user_id'] = user_id
        if limit:
            params['limit'] = limit
        return self._get(params=params)

    def show_invocation(self, invocation_id):
        """
        Get a workflow invocation dictionary representing the scheduling of a
        workflow. This dictionary may be sparse at first (missing inputs and
        invocation steps) and will become more populated as the workflow is
        actually scheduled.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: dict
        :return: The workflow invocation.
          For example::

            {'history_id': '2f94e8ae9edff68a',
             'id': 'df7a1f0c02a5b08e',
             'inputs': {'0': {'id': 'a7db2fac67043c7e',
               'src': 'hda',
               'uuid': '7932ffe0-2340-4952-8857-dbaa50f1f46a'}},
             'model_class': 'WorkflowInvocation',
             'state': 'ready',
             'steps': [{'action': None,
               'id': 'd413a19dec13d11e',
               'job_id': None,
               'model_class': 'WorkflowInvocationStep',
               'order_index': 0,
               'state': None,
               'update_time': '2015-10-31T22:00:26',
               'workflow_step_id': 'cbbbf59e8f08c98c',
               'workflow_step_label': None,
               'workflow_step_uuid': 'b81250fd-3278-4e6a-b269-56a1f01ef485'},
              {'action': None,
               'id': '2f94e8ae9edff68a',
               'job_id': 'e89067bb68bee7a0',
               'model_class': 'WorkflowInvocationStep',
               'order_index': 1,
               'state': 'new',
               'update_time': '2015-10-31T22:00:26',
               'workflow_step_id': '964b37715ec9bd22',
               'workflow_step_label': None,
               'workflow_step_uuid': 'e62440b8-e911-408b-b124-e05435d3125e'}],
             'update_time': '2015-10-31T22:00:26',
             'uuid': 'c8aa2b1c-801a-11e5-a9e5-8ca98228593c',
             'workflow_id': '03501d7626bd192f'}
        """
        url = self._make_url(invocation_id)
        return self._get(url=url)

    def cancel_invocation(self, invocation_id):
        """
        Cancel the scheduling of a workflow.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: dict
        :return: The workflow invocation being cancelled
        """
        url = self._make_url(invocation_id)
        return self._delete(url=url)

    def show_invocation_step(self, invocation_id, step_id):
        """
        See the details of a particular workflow invocation step.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :type step_id: str
        :param step_id: Encoded workflow invocation step ID

        :rtype: dict
        :return: The workflow invocation step.
          For example::

            {'action': None,
             'id': '63cd3858d057a6d1',
             'job_id': None,
             'model_class': 'WorkflowInvocationStep',
             'order_index': 2,
             'state': None,
             'update_time': '2015-10-31T22:11:14',
             'workflow_step_id': '52e496b945151ee8',
             'workflow_step_label': None,
             'workflow_step_uuid': '4060554c-1dd5-4287-9040-8b4f281cf9dc'}
        """
        url = self._invocation_step_url(invocation_id, step_id)
        return self._get(url=url)

    def run_invocation_step_action(self, invocation_id, step_id, action):
        """ Execute an action for an active workflow invocation step. The
        nature of this action and what is expected will vary based on the
        the type of workflow step (the only currently valid action is True/False
        for pause steps).

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :type step_id: str
        :param step_id: Encoded workflow invocation step ID

        :type action: object
        :param action: Action to use when updating state, semantics depends on
           step type.

        :rtype: dict
        :return: Representation of the workflow invocation step
        """
        url = self._invocation_step_url(invocation_id, step_id)
        payload = {"action": action}
        return self._put(payload=payload, url=url)

    def get_invocation_summary(self, invocation_id):
        """
        Get a summary of an invocation, stating the number of jobs which
        succeed, which are paused and which have errored.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: dict
        :return: The invocation summary.
          For example::

            {'states': {'paused': 4, 'error': 2, 'ok': 2},
             'model': 'WorkflowInvocation',
             'id': 'a799d38679e985db',
             'populated_state': 'ok'}
        """
        url = self._make_url(invocation_id) + '/jobs_summary'
        return self._get(url=url)

    def get_invocation_step_jobs_summary(self, invocation_id):
        """
        Get a detailed summary of an invocation, listing all jobs with
        their job IDs and current states.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: list of dicts
        :return: The invocation step jobs summary.
          For example::
            [
                {'populated_state': 'ok',
                 'states': {'ok': 1},
                 'model': 'Job',
                 'id': 'e85a3be143d5905b'},

                {'populated_state': 'ok',
                 'states': {'running': 1},
                 'model': 'Job',
                 'id': 'c9468fdb6dc5c5f1'}

                {'populated_state': 'ok',
                 'states': {'new': 1},
                 'model': 'Job',
                 'id': '2a56795cad3c7db3'}
            ]
        """
        url = self._make_url(invocation_id) + '/step_jobs_summary'
        return self._get(url=url)

    def get_invocation_report(self, invocation_id):
        """
        Get a Markdown report for an invocation.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: dict
        :return: The invocation report.
          For example::

            {'markdown': '\\n# Workflow Execution Summary of Example workflow\\n\\n
             ## Workflow Inputs\\n\\n\\n## Workflow Outputs\\n\\n\\n
             ## Workflow\\n```galaxy\\n
             workflow_display(workflow_id=f2db41e1fa331b3e)\\n```\\n',
             'render_format': 'markdown',
             'workflows': {'f2db41e1fa331b3e': {'name': 'Example workflow'}}}
        """
        url = self._make_url(invocation_id) + '/report'
        return self._get(url=url)

    def get_invocation_report_pdf(self, invocation_id, file_path, chunk_size=CHUNK_SIZE):
        """
        Get a PDF report for an invocation.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :type file_path: str
        :param file_path: Path to save the report
        """
        url = self._make_url(invocation_id) + '/report.pdf'
        r = self.gi.make_get_request(url, stream=True)
        if r.status_code != 200:
            raise Exception("Failed to get the PDF report, the necessary dependencies may not be installed on the Galaxy server.")
        with open(file_path, 'wb') as outf:
            for chunk in r.iter_content(chunk_size):
                outf.write(chunk)

    def get_invocation_biocompute_object(self, invocation_id):
        """
        Get a BioCompute object for an invocation.

        :type invocation_id: str
        :param invocation_id: Encoded workflow invocation ID

        :rtype: dict
        :return: The BioCompute object
        """
        url = self._make_url(invocation_id) + '/biocompute'
        return self._get(url=url)

    def wait_for_invocation(self, invocation_id, maxwait=12000, interval=3, check=True):
        """
        Wait until an invocation is in a terminal state.

        :type invocation_id: str
        :param invocation_id: Invocation ID to wait for.

        :type maxwait: float
        :param maxwait: Total time (in seconds) to wait for the invocation state
          to become terminal. If the invocation state is not terminal within
          this time, a ``TimeoutException`` will be raised.

        :type interval: float
        :param interval: Time (in seconds) to wait between 2 consecutive checks.

        :type check: bool
        :param check: Whether to check if the invocation terminal state is
          'scheduled'.

        :rtype: dict
        :return: Details of the workflow invocation.
        """
        assert maxwait >= 0
        assert interval > 0

        time_left = maxwait
        while True:
            invocation = self.gi.invocations.show_invocation(invocation_id)
            state = invocation['state']
            if state in INVOCATION_TERMINAL_STATES:
                if check and state != 'scheduled':
                    raise Exception(f"Invocation {invocation_id} is in terminal state {state}")
                return invocation
            if time_left > 0:
                log.info(f"Invocation {invocation_id} is in non-terminal state {state}. Will wait {time_left} more s")
                time.sleep(min(time_left, interval))
                time_left -= interval
            else:
                raise TimeoutException(f"Invocation {invocation_id} is still in non-terminal state {state} after {maxwait} s")

    def _invocation_step_url(self, invocation_id, step_id):
        return '/'.join((self._make_url(invocation_id), "steps", step_id))


__all__ = ('InvocationClient',)
