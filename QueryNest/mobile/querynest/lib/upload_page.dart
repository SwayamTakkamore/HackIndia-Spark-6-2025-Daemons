import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:io';

class UploadPage extends StatefulWidget {
  final Function(String) onUploadSuccess;

  const UploadPage({super.key, required this.onUploadSuccess});

  @override
  _UploadPageState createState() => _UploadPageState();
}

class _UploadPageState extends State<UploadPage> {
  bool _isUploading = false;
  String? _fileName;

  Future<void> _uploadFile() async {
    setState(() => _isUploading = true);
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf'],
      );

      if (result != null) {
        setState(() {
          _fileName = result.files.single.name;
        });

        final file = File(result.files.single.path!);
        var request = http.MultipartRequest('POST', Uri.parse('http://192.168.54.199:8000/upload'));
        request.files.add(await http.MultipartFile.fromPath('file', file.path));

        final response = await http.Response.fromStream(await request.send());
        if (response.statusCode == 200) {
          widget.onUploadSuccess(file.path);
        }
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error uploading file: $e')),
      );
    } finally {
      setState(() => _isUploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('DocQuery'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.upload_file,
                size: 80,
                color: Colors.blue,
              ),
              const SizedBox(height: 20),
              const Text(
                'Upload a PDF document to get started',
                style: TextStyle(fontSize: 18),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 30),
              if (_fileName != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 20),
                  child: Text(
                    'Selected file: $_fileName',
                    style: const TextStyle(fontStyle: FontStyle.italic),
                  ),
                ),
              _isUploading
                  ? const CircularProgressIndicator()
                  : ElevatedButton.icon(
                onPressed: _uploadFile,
                icon: const Icon(Icons.file_upload),
                label: const Text('Upload PDF'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 24, vertical: 12),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}