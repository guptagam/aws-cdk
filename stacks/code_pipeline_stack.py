from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_codebuild as cb,
    aws_codepipeline as cp,
    aws_codecommit as cc,
    aws_codepipeline_actions as cpa,
    aws_iam as iam

)
from utils.code_build_project import CodeBuildProject as cbp
import yaml
import os
class PipelineStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        project_name = self.node.try_get_context("project_name")
        try:
            stage = os.environ['STAGE']
        except KeyError as err:
            print("Environment variable STAGE is not set") 

        source_output = cp.Artifact()
        
        code = cc.Repository.from_repository_name(self, "ImportedRepo-dev",'aws-cdk')
        source_action = cpa.CodeCommitSourceAction(action_name="CodeCommit_Source",
                            repository=code,
                            output=source_output,
                            branch = stage
        )
        print(stage)
        config = self.readConfig(stage)    
        modules = config["modules"]
        #iterating through the modules
        stack_projects = []
        for project in modules:
            build_project = cbp.build_pipeline_project(self,f"{project['name']}-{stage}",f"{project['name']}",stage)
            build_project.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess'))
            build_output = cp.Artifact(f"{project['name']}-output")
            stack_project = cbp.build_code_pipeline_action_project(f"{project['name']}-{stage}",
                                                                    build_project,
                                                                    source_output,
                                                                    build_output,
                                                                    source_action,
                                                                    run_order= project['runOrder']
            )
            stack_projects.append(stack_project)
        cp.Pipeline(self, "Pipeline",
            stages=[
                cp.StageProps(stage_name="Source",
                    actions=[source_action]),
                cp.StageProps(stage_name="Build",
                    actions=stack_projects
                )
            ], pipeline_name= f'deploying-to-{stage}'
        )
        

    def readConfig(self,stage):
        with open(f"config/{stage}.yml", 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)