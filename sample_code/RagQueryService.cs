using System.Text.Json;
using ViskAnna.Ollama.Clients;
using ViskAnna.Ollama.Models;
using ViskAnna.Rag.Models;

namespace ViskAnna.Rag.Services
{
    public interface IRagQueryService
    {
        Task<RagQueryResponse> QueryAsync(RagQueryRequest request);
    }

    public class RagQueryService : IRagQueryService
    {
        private readonly IWeaviateService _weaviateService;
        private readonly IEmbeddingService _embeddingService;
        private readonly OllamaClient _ollamaClient;
        private readonly ILogger<RagQueryService> _logger;
        private readonly string _chatModel;

        private const string SystemPromptTemplate = @"You are a helpful eCommerce assistant for ViskAnna. Your role is to help users with:
- Finding customers and information about them
- Understanding how to navigate the website
- Answering questions about orders and shopping

IMPORTANT INSTRUCTIONS:
1. Answer based ONLY on the context provided below
2. If the information is not in the context, say ""I don't have that information in my knowledge base""
3. Be concise and helpful
4. If asked about customers, include relevant details like purchase history when available
5. If asked about navigation, provide clear step-by-step instructions
6. Always be polite and professional

CONTEXT:
{0}

Remember: Only use information from the context above. Do not make up information.";

        public RagQueryService(
            IWeaviateService weaviateService,
            IEmbeddingService embeddingService,
            OllamaClient ollamaClient,
            ILogger<RagQueryService> logger,
            IConfiguration configuration)
        {
            _weaviateService = weaviateService;
            _embeddingService = embeddingService;
            _ollamaClient = ollamaClient;
            _logger = logger;
            _chatModel = configuration["Ollama:ChatModel"] ?? "gpt-oss:20b";
        }

        public async Task<RagQueryResponse> QueryAsync(RagQueryRequest request)
        {
            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            var response = new RagQueryResponse { Model = _chatModel };

            try
            {
                _logger.LogInformation("Processing RAG query: {Query}", request.Query);

                var queryEmbedding = await _embeddingService.GetEmbeddingAsync(request.Query);

                var allResults = new List<(WeaviateSearchResult Result, string Collection)>();

                foreach (var collection in request.Collections)
                {
                    var results = await _weaviateService.SemanticSearchAsync(
                        queryEmbedding,
                        collection,
                        request.MaxResults);

                    allResults.AddRange(results.Select(r => (r, collection)));
                }

                var sortedResults = allResults
                    .OrderBy(r => r.Result.Additional?.Distance ?? double.MaxValue)
                    .Take(request.MaxResults)
                    .ToList();

                if (request.IncludeSources)
                {
                    response.Sources = sortedResults.Select(r => new SourceDocument
                    {
                        Collection = r.Collection,
                        Content = r.Result.Content,
                        Score = 1 - (r.Result.Additional?.Distance ?? 0),
                        Metadata = ParseMetadata(r.Result.Metadata)
                    }).ToList();
                }

                var context = BuildContext(sortedResults);

                var chatRequest = new OllamaChatRequest
                {
                    Model = _chatModel,
                    Stream = false,
                    Messages = new List<OllamaChatMessage>
                    {
                        new()
                        {
                            Role = "system",
                            Content = string.Format(SystemPromptTemplate, context)
                        },
                        new()
                        {
                            Role = "user",
                            Content = request.Query
                        }
                    }
                };

                var chatResponse = await _ollamaClient.ChatAsync(chatRequest);
                response.Answer = chatResponse.Message?.Content ?? "I'm sorry, I couldn't generate a response.";

                stopwatch.Stop();
                response.QueryTimeMs = stopwatch.ElapsedMilliseconds;

                _logger.LogInformation(
                    "RAG query completed in {Time}ms with {Sources} sources",
                    response.QueryTimeMs,
                    response.Sources.Count);

                return response;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error processing RAG query");
                stopwatch.Stop();
                response.QueryTimeMs = stopwatch.ElapsedMilliseconds;
                response.Answer = "I'm sorry, an error occurred while processing your question. Please try again.";
                return response;
            }
        }

        private static string BuildContext(List<(WeaviateSearchResult Result, string Collection)> results)
        {
            if (!results.Any())
            {
                return "No relevant information found.";
            }

            var contextParts = new List<string>();

            var customerResults = results.Where(r => r.Collection == "Customers").ToList();
            if (customerResults.Any())
            {
                contextParts.Add("=== CUSTOMER INFORMATION ===");
                foreach (var (result, _) in customerResults)
                {
                    contextParts.Add(result.Content);
                    contextParts.Add("---");
                }
            }

            var navResults = results.Where(r => r.Collection == "WebsiteNavigation").ToList();
            if (navResults.Any())
            {
                contextParts.Add("=== WEBSITE NAVIGATION ===");
                foreach (var (result, _) in navResults)
                {
                    contextParts.Add(result.Content);
                    contextParts.Add("---");
                }
            }

            var otherResults = results.Where(r => r.Collection != "Customers" && r.Collection != "WebsiteNavigation").ToList();
            if (otherResults.Any())
            {
                contextParts.Add("=== ADDITIONAL INFORMATION ===");
                foreach (var (result, collection) in otherResults)
                {
                    contextParts.Add($"[{collection}]");
                    contextParts.Add(result.Content);
                    contextParts.Add("---");
                }
            }

            return string.Join("\n", contextParts);
        }

        private static Dictionary<string, object> ParseMetadata(string metadataJson)
        {
            if (string.IsNullOrWhiteSpace(metadataJson))
            {
                return new Dictionary<string, object>();
            }

            try
            {
                return JsonSerializer.Deserialize<Dictionary<string, object>>(metadataJson)
                    ?? new Dictionary<string, object>();
            }
            catch
            {
                return new Dictionary<string, object>();
            }
        }
    }
}
