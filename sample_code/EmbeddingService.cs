using ViskAnna.Ollama.Clients;
using ViskAnna.Ollama.Models;

namespace ViskAnna.Rag.Services
{
    public interface IEmbeddingService
    {
        Task<List<double>> GetEmbeddingAsync(string text);
        Task<List<List<double>>> GetEmbeddingsAsync(List<string> texts);
    }

    public class EmbeddingService : IEmbeddingService
    {
        private readonly OllamaClient _ollamaClient;
        private readonly ILogger<EmbeddingService> _logger;
        private readonly string _embeddingModel;

        public EmbeddingService(
            OllamaClient ollamaClient,
            ILogger<EmbeddingService> logger,
            IConfiguration configuration)
        {
            _ollamaClient = ollamaClient;
            _logger = logger;
            _embeddingModel = configuration["Ollama:EmbeddingModel"] ?? "embeddinggemma:latest";
        }

        public async Task<List<double>> GetEmbeddingAsync(string text)
        {
            try
            {
                var request = new OllamaEmbedRequest
                {
                    Model = _embeddingModel,
                    Input = new List<string> { text }
                };

                var response = await _ollamaClient.EmbedAsync(request);

                if (response.Embeddings.Any())
                {
                    return response.Embeddings[0];
                }

                _logger.LogWarning("No embeddings returned for text");
                return new List<double>();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error getting embedding");
                throw;
            }
        }

        public async Task<List<List<double>>> GetEmbeddingsAsync(List<string> texts)
        {
            try
            {
                var request = new OllamaEmbedRequest
                {
                    Model = _embeddingModel,
                    Input = texts
                };

                var response = await _ollamaClient.EmbedAsync(request);
                return response.Embeddings;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error getting embeddings for batch");
                throw;
            }
        }
    }
}
