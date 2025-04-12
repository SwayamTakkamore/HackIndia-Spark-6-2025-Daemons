import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:querynest/prompt_page.dart';
import 'package:querynest/results_page.dart';
import 'package:querynest/upload_page.dart';
import 'package:querynest/summary_page.dart';
import 'package:querynest/documents_page.dart';

void main() {
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      systemNavigationBarColor: Colors.white,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const DocQueryApp());
}

class DocQueryApp extends StatefulWidget {
  const DocQueryApp({super.key});

  @override
  State<DocQueryApp> createState() => _DocQueryAppState();
}

class _DocQueryAppState extends State<DocQueryApp> {
  String? activeDocumentId;

  void setActiveDocument(String docId) {
    setState(() {
      activeDocumentId = docId;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      initialRoute: '/documents',
      routes: {
        '/upload':
            (context) => UploadPage(
              onUploadSuccess:
                  (path) => Navigator.pushNamed(context, '/documents'),
            ),
        '/documents':
            (context) => DocumentsPage(
              onDocumentSelected: (docId) {
                setActiveDocument(docId);
                Navigator.pushNamed(context, '/prompt');
              },
            ),
        '/prompt':
            (context) => PromptPage(
              documentId: activeDocumentId,
              onQuerySubmit: (query) async {
              },
              onSummaryRequest: () async {
                showDialog(
                  context: context,
                  barrierDismissible: false,
                  builder: (BuildContext context) {
                    return const Center(child: CircularProgressIndicator());
                  },
                );

                try {
                  final Uri uri = Uri.parse(
                    'http://192.168.54.199:8000/summary',
                  );
                  final Map<String, String> queryParams = {
                    'validate': 'true',
                    if (activeDocumentId != null) 'doc_id': activeDocumentId!,
                  };

                  final response = await http.get(
                    uri.replace(queryParameters: queryParams),
                  );

                  Navigator.pop(context);

                  final data = jsonDecode(response.body);
                  final summary = data['summary'];
                  final validation =
                      data['validation'] != null
                          ? ValidationInfo.fromJson(data['validation'])
                          : null;

                  Navigator.pushNamed(
                    context,
                    '/summary',
                    arguments: {'summary': summary, 'validation': validation},
                  );
                } catch (e) {
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Error fetching summary: $e')),
                  );
                }
              },
              onTopicSummaryRequest: (query) async {},
            ),
        '/results':
            (context) => ResultsPage(
              result: ModalRoute.of(context)!.settings.arguments as String,
            ),
        '/summary': (context) {
          final args = ModalRoute.of(context)!.settings.arguments;
          if (args is Map) {
            return SummaryPage(
              summary: args['summary'],
              validation: args['validation'],
            );
          } else {
            return SummaryPage(summary: args as String);
          }
        },
      },
    );
  }
}
