import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

class Document {
  final String id;
  final String name;
  final int? size;
  final DateTime? uploadDate;

  Document({
    required this.id,
    required this.name,
    this.size,
    this.uploadDate
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'],
      name: json['name'],
      size: json['size'],
      uploadDate: json['upload_date'] != null
          ? DateTime.tryParse(json['upload_date'])
          : null,
    );
  }
}

class DocumentsPage extends StatefulWidget {
  final Function(String) onDocumentSelected;

  const DocumentsPage({
    Key? key,
    required this.onDocumentSelected
  }) : super(key: key);

  @override
  _DocumentsPageState createState() => _DocumentsPageState();
}

class _DocumentsPageState extends State<DocumentsPage> {
  List<Document> documents = [];
  bool isLoading = true;
  String? activeDocumentId;

  @override
  void initState() {
    super.initState();
    _loadDocuments();
  }

  Future<void> _loadDocuments() async {
    setState(() {
      isLoading = true;
    });

    try {
      final response = await http.get(
        Uri.parse('http://192.168.54.199:8000/documents'),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        setState(() {
          documents = data.map((doc) => Document.fromJson(doc)).toList();
          // Set the first document as active if available
          if (documents.isNotEmpty && activeDocumentId == null) {
            activeDocumentId = documents.first.id;
          }
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading documents: ${response.statusCode}')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Network error: $e')),
      );
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> _activateDocument(String docId) async {
    try {
      final response = await http.post(
        Uri.parse('http://192.168.54.199:8000/documents/$docId/activate'),
      );

      if (response.statusCode == 200) {
        setState(() {
          activeDocumentId = docId;
        });
        widget.onDocumentSelected(docId);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not activate document')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Network error: $e')),
      );
    }
  }

  Future<void> _deleteDocument(String docId) async {
    try {
      final response = await http.delete(
        Uri.parse('http://192.168.54.199:8000/documents/$docId'),
      );

      if (response.statusCode == 200) {
        _loadDocuments();  // Refresh the list
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not delete document')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Network error: $e')),
      );
    }
  }

  String _formatFileSize(int? bytes) {
    if (bytes == null) return 'Unknown size';

    const suffixes = ['B', 'KB', 'MB', 'GB'];
    var i = 0;
    double size = bytes.toDouble();

    while (size > 1024 && i < suffixes.length - 1) {
      size /= 1024;
      i++;
    }

    return '${size.toStringAsFixed(1)} ${suffixes[i]}';
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'Unknown date';
    return DateFormat('MMM d, yyyy • h:mm a').format(date);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Your Documents'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDocuments,
            tooltip: 'Refresh documents',
          ),
        ],
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : documents.isEmpty
          ? Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.folder_open,
              size: 70,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            const Text(
              'No documents found',
              style: TextStyle(
                fontSize: 18,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pushNamed(context, '/upload'),
              child: const Text('Upload a Document'),
            ),
          ],
        ),
      )
          : ListView.builder(
        itemCount: documents.length,
        itemBuilder: (context, index) {
          final doc = documents[index];
          final isActive = doc.id == activeDocumentId;

          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: isActive ? Colors.blue.shade50 : null,
            child: ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.blue.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.description, color: Colors.blue),
              ),
              title: Text(
                doc.name,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_formatFileSize(doc.size)),
                  Text(
                    _formatDate(doc.uploadDate),
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (isActive)
                    const Chip(
                      label: Text('Active'),
                      backgroundColor: Colors.green,
                      labelStyle: TextStyle(color: Colors.white),
                    )
                  else
                    IconButton(
                      icon: const Icon(Icons.check_circle_outline),
                      tooltip: 'Set as active',
                      onPressed: () => _activateDocument(doc.id),
                    ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, color: Colors.red),
                    tooltip: 'Delete document',
                    onPressed: () => showDialog(
                      context: context,
                      builder: (context) => AlertDialog(
                        title: const Text('Delete Document'),
                        content: Text('Are you sure you want to delete "${doc.name}"?'),
                        actions: [
                          TextButton(
                            onPressed: () => Navigator.pop(context),
                            child: const Text('Cancel'),
                          ),
                          TextButton(
                            onPressed: () {
                              Navigator.pop(context);
                              _deleteDocument(doc.id);
                            },
                            child: const Text('Delete', style: TextStyle(color: Colors.red)),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              onTap: () => _activateDocument(doc.id),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => Navigator.pushNamed(context, '/upload'),
        child: const Icon(Icons.add),
        tooltip: 'Upload new document',
      ),
    );
  }
}
