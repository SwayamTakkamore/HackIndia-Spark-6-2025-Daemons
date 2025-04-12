import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class ValidationInfo {
  final bool isValid;
  final double score;
  final String message;
  final String? confidence;
  final double? factValidity;
  final double? queryRelevance;

  ValidationInfo({
    required this.isValid,
    required this.score,
    required this.message,
    this.confidence,
    this.factValidity,
    this.queryRelevance,
  });

  factory ValidationInfo.fromJson(Map<String, dynamic> json) {
    return ValidationInfo(
      isValid: json['valid'] ?? false,
      score: (json['score'] ?? 0.0).toDouble(),
      message: json['message'] ?? 'No validation information',
      confidence: json['confidence'],
      factValidity:
          json['fact_validity']?.toDouble(),
      queryRelevance:
          json['query_relevance']?.toDouble(),
    );
  }
}

class SummaryPage extends StatelessWidget {
  final String summary;
  final ValidationInfo? validation;

  const SummaryPage({super.key, required this.summary, this.validation});

  @override
  Widget build(BuildContext context) {
    final bool isTopicSummary = summary.startsWith("Topic:");
    String title = 'Document Summary';
    Color cardColor = Colors.blue[50]!;
    Icon headerIcon = const Icon(Icons.summarize);

    if (isTopicSummary) {
      title = 'Topic Summary';
      cardColor = Colors.green[50]!;
      headerIcon = const Icon(Icons.topic, color: Colors.green);
    }

    final bool isError =
        summary.startsWith("Error") ||
        summary.startsWith("Could not") ||
        summary.startsWith("Unable to");

    final bool isKeyPoints =
        summary.startsWith("Key points") ||
        summary.startsWith("Document overview") ||
        summary.startsWith("Document preview");

    if (isError) {
      title = 'Error';
      cardColor = Colors.red[50]!;
      headerIcon = const Icon(Icons.error_outline, color: Colors.red);
    } else if (isKeyPoints) {
      title = 'Key Points';
      cardColor = Colors.amber[50]!;
      headerIcon = const Icon(Icons.lightbulb_outline, color: Colors.orange);
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          IconButton(
            icon: const Icon(Icons.copy),
            tooltip: 'Copy to clipboard',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: summary));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Summary copied to clipboard')),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                elevation: 4,
                color: cardColor,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          headerIcon,
                          const SizedBox(width: 8),
                          Text(
                            title,
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color:
                                  isError
                                      ? Colors.red[700]
                                      : (isKeyPoints
                                          ? Colors.orange[700]
                                          : (isTopicSummary
                                              ? Colors.green[700]
                                              : Colors.blue[700])),
                            ),
                          ),
                          const Spacer(),
                          if (validation != null)
                            _buildValidationBadge(validation!),
                        ],
                      ),
                      const Divider(height: 24),
                      Text(
                        summary,
                        style: TextStyle(
                          fontSize: 16,
                          height: 1.5,
                          color: isError ? Colors.red[800] : Colors.black87,
                        ),
                      ),
                      if (validation != null) ...[
                        const Divider(height: 32),
                        _buildValidationDetails(validation!),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Back to Query'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildValidationBadge(ValidationInfo validation) {
    Color badgeColor;
    IconData iconData;
    String label;

    if (validation.isValid) {
      badgeColor = Colors.green;
      iconData = Icons.verified;
      label = validation.confidence == 'High' ? 'High Accuracy' : 'Valid';
    } else {
      badgeColor = Colors.orange;
      iconData = Icons.warning_amber;
      label = 'Needs Review';
    }

    return Chip(
      backgroundColor: badgeColor,
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(iconData, color: Colors.white, size: 16),
          const SizedBox(width: 4),
          Text(label, style: const TextStyle(color: Colors.white)),
        ],
      ),
    );
  }

  Widget _buildValidationDetails(ValidationInfo validation) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Validation Results',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        _buildValidationRow(
          'Accuracy Score',
          '${(validation.score * 100).toStringAsFixed(1)}%',
          validation.score,
        ),
        if (validation.factValidity != null)
          _buildValidationRow(
            'Factual Validity',
            '${(validation.factValidity! * 100).toStringAsFixed(1)}%',
            validation.factValidity!,
          ),
        if (validation.queryRelevance != null)
          _buildValidationRow(
            'Query Relevance',
            '${(validation.queryRelevance! * 100).toStringAsFixed(1)}%',
            validation.queryRelevance!,
          ),
        const SizedBox(height: 8),
        Text(
          validation.message,
          style: TextStyle(
            fontStyle: FontStyle.italic,
            color: validation.isValid ? Colors.green[700] : Colors.orange[700],
          ),
        ),
      ],
    );
  }

  Widget _buildValidationRow(String label, String value, double score) {
    Color getScoreColor() {
      if (score >= 0.8) return Colors.green;
      if (score >= 0.6) return Colors.orange;
      return Colors.red;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text('$label: '),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: getScoreColor().withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: getScoreColor()),
            ),
            child: Text(
              value,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: getScoreColor(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
