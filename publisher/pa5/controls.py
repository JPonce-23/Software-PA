"""Fail closed unless pa5-publish has owner review and a main-only branch policy."""
import json
import os
import urllib.request
from pa5_supply import require

ROOT = 'https://api.github.com/repos/JPonce-23/Software-PA/environments/pa5-publish'


def validate(environment, policies):
    rules = environment.get('protection_rules', [])
    review = [rule for rule in rules if rule.get('type') == 'required_reviewers']
    require(len(review) == 1, 'ENVIRONMENT_REQUIRED_REVIEWERS_MISSING')
    require(any(item.get('type') == 'User' and item.get('reviewer', {}).get('login') == 'JPonce-23'
                for item in review[0].get('reviewers', [])), 'OWNER_MUST_BE_ENVIRONMENT_REVIEWER')
    # Required reviewers uses OR semantics. Only the owner may approve this initial publication.
    require(len(review[0]['reviewers']) == 1, 'OWNER_MUST_BE_SOLE_INITIAL_REVIEWER')
    # GitHub's GET schema does not guarantee the admin-bypass setting is returned.
    # The owner must check that setting in the UI; reject it when exposed as enabled.
    require(environment.get('can_admins_bypass') is not True, 'DISABLE_ADMIN_BYPASS')
    require(environment.get('deployment_branch_policy') ==
            {'protected_branches': False, 'custom_branch_policies': True}, 'MAIN_BRANCH_POLICY_REQUIRED')
    branches = policies.get('branch_policies', [])
    require(len(branches) == 1 and branches[0].get('name') == 'main' and
            branches[0].get('type') == 'branch', 'EXACT_MAIN_BRANCH_ONLY')


def get(path):
    request = urllib.request.Request(ROOT + path, headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'software-pa-pa5-publisher'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


if __name__ == '__main__':
    validate(get(''), get('/deployment-branch-policies'))
    print('PA5_PUBLISH_OWNER_REVIEW_AND_MAIN_ONLY_POLICY_VERIFIED')
