import argparse
import os
import json
import requests
import gitlab

config = {}

def main():

    parser = argparse.ArgumentParser(description='Generate gitlab branch report')
    parser.add_argument('--url', default='https://gitlab.com',
                    help='Gitlab url (default: https://gitlab.com)')
    parser.add_argument('--group', type=int, required=True,
                    help='Gitlab group ID')
    parser.add_argument('--token',
                    help='Gitlab private token or $BW_GITLAB_TOKEN')
    parser.add_argument('--webhook',
                    help='Webhook url or $BW_WEBHOOK')
    args = parser.parse_args()

    config['gitlab_url'] = args.url
    config['gitlab_group'] = args.group
    config['gitlab_token'] = args.token or os.getenv('BW_GITLAB_TOKEN')
    config['webhook_url'] = args.webhook or os.getenv('BW_WEBHOOK')

    report = generate_branch_report()
    send_report(report)


def generate_branch_report():
    report = {
        'pendingReviewBranches': [],
        'wipBranches': [],
        'untrackedBranches': [],
    }
    gl = gitlab.Gitlab(config['gitlab_url'], private_token=config['gitlab_token'])
    group = gl.groups.get(config['gitlab_group'])

    # Retrieve opened merge requests
    group_merge_requests = group.mergerequests.list(state='opened')
    for mr in group_merge_requests:
        message = '* %s `%s` -> `%s` : %s' % (mr.title, mr.source_branch, mr.target_branch, mr.web_url)
        if mr.work_in_progress:
            report['wipBranches'].append(message)
        else:
            report['pendingReviewBranches'].append(message)

    # Iterate over project to find active branches
    for groupProject in group.projects.list():
        project = gl.projects.get(groupProject.id)
        for branch in project.branches.list():
            # Exclude master branch, protected branches and merged branches
            if branch.name == 'master' or branch.protected or branch.merged:
                continue

            # Find associated merge request (if any)
            mr_opened = False
            for mr in group_merge_requests:
                if mr.project_id == project.id and mr.source_branch == branch.name:
                    mr_opened = True
                    break
            
            if not mr_opened:
                message = '* `%s` on %s (last commit by %s)' % (branch.name, project.name, branch.commit['author_name'])
                report['untrackedBranches'].append(message)

    return report


def send_report(report):
    
    data = ':rocket: **Pending Review** \n'
    data += '\n'.join(report['pendingReviewBranches'])
    data += '\n:stopwatch: **Work in progress**\n'
    data += '\n'.join(report['wipBranches'])
    data += '\n:black_flag: **Untracked work**\n'
    data += '\n'.join(report['untrackedBranches'])
    print(data)

    body = {'text': data}
    response = requests.post(
        config['webhook_url'], data=json.dumps(body),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )


if __name__ == '__main__':
    # execute only if run as a script
    main()
