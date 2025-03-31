import json
from launch_instance import launch_ytdlp_instance


def handler(event, context):
    # Extract path parameters if they exist
    path_parameters = event.get("pathParameters", {}) or {}

    # Get query string parameters if they exist
    query_parameters = event.get("queryStringParameters", {}) or {}

    # Get HTTP method
    http_method = event.get("httpMethod", "")

    # Process the request based on the method
    if http_method == "GET":
        if "video_id" in query_parameters:
            launch_ytdlp_instance(
                video_id=query_parameters["video_id"],
                s3_bucket="cloudytdl-20250330150643",
                path=query_parameters.get("path", "music"),
            )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": f"Retrieving video: {query_parameters.get('video_id')}",
                    "path_parameters": path_parameters,
                    "query_parameters": query_parameters,
                }
            ),
            "headers": {"Content-Type": "application/json"},
        }
    elif http_method == "POST":
        # Parse the body if it exists
        body = {}
        if "body" in event and event["body"]:
            body = json.loads(event["body"])

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "This is a POST response", "received_data": body}),
            "headers": {"Content-Type": "application/json"},
        }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": f"Unsupported method: {http_method}"}),
            "headers": {"Content-Type": "application/json"},
        }
