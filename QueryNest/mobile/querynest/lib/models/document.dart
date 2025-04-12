class Document {
  final String id;
  final String filename;
  final double score;

  Document({
    required this.id,
    required this.filename,
    required this.score,
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'].toString(),
      filename: json['filename'],
      score: json['score']?.toDouble() ?? 0,
    );
  }
}