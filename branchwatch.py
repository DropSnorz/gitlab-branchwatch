import gitlab
import json
import requests

config = {}
config["gitlab_url"] = "https://gitlab.com"
config["gitlab_token"] = "secret"
config["gitlab_group"] = 6337446
config["webhook_url"] = "secret"

def main():
    report = generate_branch_report();
    send_report(report)


def generate_branch_report():
    report = {
        "pendingReviewBranches": [],
        "wipBranches": [],
        "untrackedBranches": [],
    }
    gl = gitlab.Gitlab(config['gitlab_url'], private_token=config['gitlab_token'])

    group = gl.groups.get(config["gitlab_group"])
    group_merge_requests = group.mergerequests.list()

    for mr in group_merge_requests:
        message = "* %s `%s` -> `%s` : %s" % (mr.title, mr.source_branch, mr.target_branch, mr.web_url)
        if mr.work_in_progress:
            report["wipBranches"].append(message);
        else:
            report["pendinReviewBranches"].append(message);


    for groupProject in group.projects.list():
        project = gl.projects.get(groupProject.id)
        for branch in project.branches.list():
            if branch.name == "master" or branch.protected or branch.merged:
                continue

            mr_opened = False
            for mr in group_merge_requests:
                if mr.project_id == project.id and mr.source_branch == branch.name:
                    mr_opened = True
                    break
            
            if not mr_opened:
                message = "* `%s` on %s (last commit by %s)" % (branch.name, project.name, branch.commit["author_name"])
                report["untrackedBranches"].append(message);

    return report


def send_report(report):
    
    data = "Pending Review \n"
    data += '\n'.join(report["pendingReviewBranches"])
    data += "\nWork in progress \n"
    data += '\n'.join(report["wipBranches"])
    data += "\nUntracked work \n"
    data += '\n'.join(report["untrackedBranches"])
    print(data)

    body = {'text': data}
    response = requests.post(
        config["webhook_url"], data=json.dumps(body),
        headers={'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    

if __name__ == "__main__":
    # execute only if run as a script
    main()
