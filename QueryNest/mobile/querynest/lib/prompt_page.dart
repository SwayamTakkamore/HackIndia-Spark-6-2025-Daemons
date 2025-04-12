import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:querynest/summary_page.dart';

class PromptPage extends StatefulWidget {
  final Function(String) onQuerySubmit;
  final Function() onSummaryRequest;
  final Function(String) onTopicSummaryRequest;
  final String? documentId;

  const PromptPage({
    super.key,
    required this.onQuerySubmit,
    required this.onSummaryRequest,
    required this.onTopicSummaryRequest,
    this.documentId,
  });

  @override
  _PromptPageState createState() => _PromptPageState();
}

class _PromptPageState extends State<PromptPage> {
  final _controller = TextEditingController();
  List<String> _documentSections = [];
  String? _selectedSection;
  bool _isLoadingSections = false;

  @override
  void initState() {
    super.initState();
    if (widget.documentId != null) {
      _loadDocumentSections(widget.documentId!);
    }
  }

  @override
  void didUpdateWidget(PromptPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.documentId != oldWidget.documentId &&
        widget.documentId != null) {
      _loadDocumentSections(widget.documentId!);
    }
  }

  Future<void> _loadDocumentSections(String docId) async {
    setState(() {
      _isLoadingSections = true;
      _selectedSection = null;
    });

    try {
      final response = await http.get(
        Uri.parse('http://192.168.54.199:8000/documents/$docId/sections'),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final sections =
            (data['sections'] as List)
                .map((section) => section['title'] as String)
                .toList();

        setState(() {
          _documentSections = sections;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error loading sections: $e')));
    } finally {
      setState(() {
        _isLoadingSections = false;
      });
    }
  }

  void _submitQuery() {
    if (_controller.text.trim().isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Please enter a query')));
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    http
        .post(
          Uri.parse('http://192.168.54.199:8000/query'),
          body: {
            'prompt': _controller.text,
            if (widget.documentId != null) 'doc_id': widget.documentId,
            if (_selectedSection != null) 'section': _selectedSection,
          },
        )
        .then((response) {
          Navigator.pop(context); // Close loading dialog
          final result = jsonDecode(response.body)['result'];
          Navigator.pushNamed(context, '/results', arguments: result);
        })
        .catchError((e) {
          Navigator.pop(context); // Close loading dialog
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('Error: $e')));
        });
  }

  void _submitTopicSummary() {
    if (_controller.text.trim().isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Please enter a topic')));
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    http
        .post(
          Uri.parse('http://192.168.54.199:8000/query_summary'),
          body: {
            'prompt': _controller.text,
            'validate': 'true',
            if (widget.documentId != null) 'doc_id': widget.documentId,
            if (_selectedSection != null) 'section': _selectedSection,
          },
        )
        .then((response) {
          Navigator.pop(context); // Close loading dialog
          final data = jsonDecode(response.body);
          final summary = data['summary'];
          final validation =
              data['validation'] != null
                  ? ValidationInfo.fromJson(data['validation'])
                  : null;

          Navigator.pushNamed(
            context,
            '/summary',
            arguments: {
              'summary': "Topic: \"${_controller.text}\"\n\n$summary",
              'validation': validation,
            },
          );
        })
        .catchError((e) {
          Navigator.pop(context); // Close loading dialog
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('Error: $e')));
        });
  }

  void _getSectionSummary() {
    if (_selectedSection == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a section first')),
      );
      return;
    }

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(child: CircularProgressIndicator()),
    );

    http
        .get(
          Uri.parse('http://192.168.54.199:8000/summary/section').replace(
            queryParameters: {
              'validate': 'true',
              if (widget.documentId != null) 'doc_id': widget.documentId,
              'section': _selectedSection!,
            },
          ),
        )
        .then((response) {
          Navigator.pop(context); // Close loading dialog
          final data = jsonDecode(response.body);
          final summary = data['summary'];
          final validation =
              data['validation'] != null
                  ? ValidationInfo.fromJson(data['validation'])
                  : null;

          Navigator.pushNamed(
            context,
            '/summary',
            arguments: {
              'summary': "Section: \"${_selectedSection}\"\n\n$summary",
              'validation': validation,
            },
          );
        })
        .catchError((e) {
          Navigator.pop(context); // Close loading dialog
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('Error: $e')));
        });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Query Document'),
        actions: [
          IconButton(
            icon: const Icon(Icons.summarize),
            tooltip: 'Get Document Summary',
            onPressed: widget.onSummaryRequest,
          ),
          IconButton(
            icon: const Icon(Icons.folder),
            tooltip: 'Switch Document',
            onPressed: () => Navigator.pushNamed(context, '/documents'),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            if (_isLoadingSections)
              const LinearProgressIndicator()
            else if (_documentSections.isNotEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Target Section',
                          hintText: 'Optional: Focus on specific section',
                          border: InputBorder.none,
                        ),
                        value: _selectedSection,
                        items: [
                          const DropdownMenuItem<String>(
                            value: null,
                            child: Text('All Sections'),
                          ),
                          ..._documentSections.map(
                            (section) => DropdownMenuItem<String>(
                              value: section,
                              child: Text(
                                section,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _selectedSection = value;
                          });
                        },
                      ),

                      // Add problem statement quick selector buttons
                      if (_documentSections.any(
                        (s) => s.toLowerCase().contains('problem statement'),
                      ))
                        Padding(
                          padding: const EdgeInsets.only(top: 8.0, bottom: 8.0),
                          child: Wrap(
                            spacing: 8.0,
                            children: [
                              const Text('Quick select:'),
                              // Find and show PS1-PS5 if they exist
                              for (int i = 1; i <= 5; i++)
                                if (_documentSections.any(
                                  (s) =>
                                      s.toLowerCase().contains(
                                        'problem statement $i',
                                      ) ||
                                      s.toLowerCase().contains('ps $i'),
                                ))
                                  FilterChip(
                                    label: Text('PS$i'),
                                    selected:
                                        _selectedSection != null &&
                                        _selectedSection!
                                            .toLowerCase()
                                            .contains('problem statement $i'),
                                    onSelected: (bool selected) {
                                      if (selected) {
                                        // Find the section
                                        String?
                                        section = _documentSections.firstWhere(
                                          (s) =>
                                              s.toLowerCase().contains(
                                                'problem statement $i',
                                              ) ||
                                              s.toLowerCase().contains('ps $i'),
                                          orElse: () => 'Problem Statement $i',
                                        );
                                        setState(() {
                                          _selectedSection = section;
                                        });
                                      } else {
                                        setState(() {
                                          _selectedSection = null;
                                        });
                                      }
                                    },
                                  ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: 'What information do you need?',
                hintText:
                    _selectedSection != null
                        ? 'e.g. Explain the main requirements'
                        : 'e.g. Tell me about Problem Statement 2',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () => _controller.clear(),
                ),
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton(
                  onPressed: _submitQuery,
                  child: const Text('Get Answer'),
                ),
                ElevatedButton(
                  onPressed: _submitTopicSummary,
                  child: const Text('Topic Summary'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: widget.onSummaryRequest,
                  icon: const Icon(Icons.summarize),
                  label: const Text('Full Document Summary'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueGrey[700],
                  ),
                ),
                if (_selectedSection != null)
                  ElevatedButton.icon(
                    onPressed: _getSectionSummary,
                    icon: const Icon(Icons.short_text),
                    label: const Text('Section Summary'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green[700],
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
