# 快手的数据传输是基于GraphQL实现的
# 这个类负责获取一些GraphQL的schema
from typing import Dict


class KuaiShouGraphQL:
    graphql_queries: Dict[str, str]= {}

    def __init__(self):
        self.graphql_dir = "media_platform/kuaishou/graphql/"
        self.load_graphql_queries()

    def load_graphql_queries(self):
        graphql_files = ["search_query.graphql", "video_detail.graphql", "comment_list.graphql"]

        for file in graphql_files:
            with open(self.graphql_dir + file, mode="r") as f:
                query_name = file.split(".")[0]
                self.graphql_queries[query_name] = f.read()

    def get(self, query_name: str) -> str:
        return self.graphql_queries.get(query_name, "Query not found")
